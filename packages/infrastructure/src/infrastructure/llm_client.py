"""Cliente LLM unificado con routing Groq + Ollama.

Reglas del proyecto:
- ``LLMRole.BRAIN`` -> Groq (llama-3.3-70b-versatile), con rate limit local.
- ``LLMRole.LIGHT`` -> Ollama local (llama3.2:3b) para clasificación rápida.
- Streaming real en ambos proveedores (SDK/event stream).
- ``complete_with_tools`` soporta function-calling con Groq; en Ollama se
  degrada a ``complete`` sin tool calls (el orchestrator ya tiene heurística).
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any

import requests
from pydantic import BaseModel, ConfigDict, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from infrastructure.settings import get_settings
from shared.errors import InfrastructureError
from shared.logging import get_logger

log = get_logger(__name__)


def rate_limit(min_interval: float = 0.5):
    """Decorator para espaciar llamadas automáticamente."""
    def decorator(func):
        last_call = {"time": 0.0}

        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_call["time"]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            result = func(*args, **kwargs)
            last_call["time"] = time.time()
            return result

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Roles + tipos
# ---------------------------------------------------------------------------


class LLMRole(str, Enum):
    """Selector lógico del modelo a usar.

    El lenguaje del proyecto: cualquier agente pide ``BRAIN`` o ``LIGHT`` —
    nadie referencia el slug exacto del modelo, así Anthropic puede renombrarlos
    sin tocar la capa de agentes.
    """

    BRAIN = "brain"   # Groq llama-3.3-70b-versatile.
    LIGHT = "light"   # Ollama llama3.2:3b.


class LLMMessage(BaseModel):
    """Mensaje en historial chat compatible OpenAI/Groq/Ollama."""

    model_config = ConfigDict(extra="forbid")

    role: str = Field(pattern="^(user|assistant)$")
    content: str


class LLMResponse(BaseModel):
    """Respuesta tipada que devuelve ``complete``/``complete_with_tools``."""

    model_config = ConfigDict(extra="forbid")

    text: str
    model: str
    stop_reason: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


@dataclass(frozen=True)
class LLMOptions:
    """Hiperparámetros razonables por defecto para la mayoría de agentes."""

    max_tokens: int = 1024
    temperature: float = 0.2
    system: str | None = None
    stop_sequences: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Backend offline (sin API key) — determinístico para tests/demo
# ---------------------------------------------------------------------------


def _offline_text(prompt: str, role: LLMRole) -> str:
    """Genera una respuesta canónica estable a partir del hash del prompt.

    Permite que la UI muestre algo coherente cuando no hay API key, y que los
    tests verifiquen contratos sin costo en créditos.
    """
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
    return (
        f"[offline:{role.value}:{digest}] "
        "Respuesta determinística -- configura GROQ_API_KEY para activar el LLM real."
    )


# ---------------------------------------------------------------------------
# Cliente principal
# ---------------------------------------------------------------------------


class LLMClient:
    """Cliente unificado con Groq (brain) y Ollama (light)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        brain_model: str | None = None,
        light_model: str | None = None,
        ollama_base_url: str | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.groq_api_key
        self._brain_model = brain_model or settings.llm_brain_model
        self._light_model = light_model or settings.llm_light_model
        self._ollama_base_url = ollama_base_url or settings.ollama_base_url
        self._sdk: Any | None = None  # Groq SDK lazy.
        self._last_groq_call = 0.0
        self._min_interval_seconds = 0.5

    # --- helpers internos -------------------------------------------------

    @property
    def is_offline(self) -> bool:
        return not bool(self._api_key)

    def _model_for(self, role: LLMRole) -> str:
        return self._brain_model if role == LLMRole.BRAIN else self._light_model

    def _ensure_sdk(self) -> Any:
        """Inicializa perezosamente el SDK Groq (solo si hay key)."""
        if self._sdk is not None:
            return self._sdk
        try:
            from groq import Groq  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - pip lo instala vía sync
            raise InfrastructureError(
                "Paquete `groq` no instalado",
                details={"hint": "uv sync"},
            ) from exc
        self._sdk = Groq(api_key=self._api_key)
        return self._sdk

    def _groq_rate_limit(self) -> None:
        elapsed = time.time() - self._last_groq_call
        if elapsed < self._min_interval_seconds:
            time.sleep(self._min_interval_seconds - elapsed)
        self._last_groq_call = time.time()

    @rate_limit(min_interval=0.5)
    def invoke(self, messages: list[dict[str, str]], max_tokens: int = 150, temperature: float = 0.3, timeout: int = 3) -> Any:
        """Invoke con rate limiting + timeout."""
        if self.is_offline:
            raise InfrastructureError("Groq API error", details={"error": "offline mode"})
        sdk = self._ensure_sdk()
        try:
            response = sdk.chat.completions.create(
                model=self._brain_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
            return response.choices[0].message
        except Exception as e:
            raise InfrastructureError("Groq API error", details={"error": str(e)}) from e

    @staticmethod
    def _build_history(
        prompt: str,
        history: list[LLMMessage] | None,
    ) -> list[dict[str, str]]:
        """Convierte historial Pydantic + prompt nuevo a la shape del SDK."""
        msgs: list[dict[str, str]] = []
        if history:
            msgs.extend(m.model_dump() for m in history)
        msgs.append({"role": "user", "content": prompt})
        return msgs

    @staticmethod
    def _to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        for t in tools:
            schema = t.get("input_schema", {"type": "object", "properties": {}})
            converted.append(
                {
                    "type": "function",
                    "function": {
                        "name": str(t.get("name", "tool")),
                        "description": str(t.get("description", "")),
                        "parameters": schema,
                    },
                }
            )
        return converted

    # --- API pública ------------------------------------------------------

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.6, min=0.6, max=4),
        retry=retry_if_exception_type(InfrastructureError),
    )
    def complete(
        self,
        prompt: str,
        *,
        role: LLMRole = LLMRole.BRAIN,
        options: LLMOptions | None = None,
        history: list[LLMMessage] | None = None,
    ) -> LLMResponse:
        """Llamada bloqueante. Devuelve ``LLMResponse`` tipada.

        En modo offline devuelve texto determinístico — útil para tests y
        para mantener la UI funcional sin créditos.
        """
        opts = options or LLMOptions()
        model = self._model_for(role)

        if self.is_offline:
            return LLMResponse(text=_offline_text(prompt, role), model=f"{model}:offline")

        if role == LLMRole.LIGHT:
            messages = self._build_history(prompt, history)
            try:
                resp = requests.post(
                    f"{self._ollama_base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": opts.temperature},
                    },
                    timeout=90,
                )
                resp.raise_for_status()
                text = resp.json().get("message", {}).get("content", "")
            except Exception as exc:
                raise InfrastructureError(
                    "Ollama completion fallo",
                    details={"model": model, "error": str(exc)},
                ) from exc
            return LLMResponse(text=text, model=f"{model}:ollama")

        sdk = self._ensure_sdk()
        self._groq_rate_limit()
        try:
            msgs = self._build_history(prompt, history)
            if opts.system:
                msgs = [{"role": "system", "content": opts.system}, *msgs]
            resp = sdk.chat.completions.create(
                model=model,
                messages=msgs,
                temperature=opts.temperature,
                max_tokens=opts.max_tokens,
            )
            msg = resp.choices[0].message
            usage = getattr(resp, "usage", None)
            return LLMResponse(
                text=msg.content or "",
                model=model,
                stop_reason=getattr(resp.choices[0], "finish_reason", None),
                input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
                output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            )
        except Exception as exc:
            raise InfrastructureError(
                "Groq completion fallo",
                details={"model": model, "error": str(exc)},
            ) from exc

    def stream(
        self,
        prompt: str,
        *,
        role: LLMRole = LLMRole.BRAIN,
        options: LLMOptions | None = None,
        history: list[LLMMessage] | None = None,
    ) -> Iterator[str]:
        """Streaming **real** de tokens (no simulado).

        Implementación: usa ``client.messages.stream(...)`` del SDK Anthropic
        con el context manager — yieldea cada delta de texto a medida que
        llega. En offline tokeniza por carácter el offline_text para que la UI
        siga animándose en demos sin créditos.
        """
        opts = options or LLMOptions()
        model = self._model_for(role)

        if self.is_offline:
            text = _offline_text(prompt, role)
            yield from text  # carácter a carácter: el SSE de la API tokeniza igual
            return

        if role == LLMRole.LIGHT:
            messages = self._build_history(prompt, history)
            try:
                with requests.post(
                    f"{self._ollama_base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": True,
                        "options": {"temperature": opts.temperature},
                    },
                    timeout=120,
                    stream=True,
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        payload = json.loads(line.decode("utf-8"))
                        token = payload.get("message", {}).get("content", "")
                        if token:
                            yield token
            except Exception as exc:
                raise InfrastructureError(
                    "Ollama streaming fallo",
                    details={"model": model, "error": str(exc)},
                ) from exc
            return

        sdk = self._ensure_sdk()
        self._groq_rate_limit()
        try:
            msgs = self._build_history(prompt, history)
            if opts.system:
                msgs = [{"role": "system", "content": opts.system}, *msgs]
            stream = sdk.chat.completions.create(
                model=model,
                messages=msgs,
                temperature=opts.temperature,
                max_tokens=opts.max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta
                token = getattr(delta, "content", None)
                if token:
                    yield token
        except Exception as exc:
            raise InfrastructureError(
                "Groq streaming fallo",
                details={"model": model, "error": str(exc)},
            ) from exc

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.6, min=0.6, max=4),
        retry=retry_if_exception_type(InfrastructureError),
    )
    def complete_with_tools(
        self,
        prompt: str,
        *,
        tools: list[dict[str, Any]],
        role: LLMRole = LLMRole.BRAIN,
        options: LLMOptions | None = None,
        history: list[LLMMessage] | None = None,
    ) -> LLMResponse:
        """Soporte de ``tool_use`` (function calling) Anthropic.

        ``tools`` sigue el schema oficial::

            {"name": "search_smogon", "description": "...",
             "input_schema": {"type": "object", "properties": {...}}}

        Devuelve ``LLMResponse`` con ``tool_calls`` rellenado cuando el
        modelo decide invocar herramientas.
        """
        opts = options or LLMOptions()
        model = self._model_for(role)

        if self.is_offline:
            return LLMResponse(
                text=_offline_text(prompt, role),
                model=f"{model}:offline",
                tool_calls=[],
            )

        if role == LLMRole.LIGHT:
            # Ollama de clasificación: degradamos a texto sin tool calls.
            return self.complete(prompt, role=role, options=options, history=history)

        sdk = self._ensure_sdk()
        self._groq_rate_limit()
        msgs = self._build_history(prompt, history)
        if opts.system:
            msgs = [{"role": "system", "content": opts.system}, *msgs]
        try:
            resp = sdk.chat.completions.create(
                model=model,
                messages=msgs,
                tools=self._to_openai_tools(tools),
                tool_choice="auto",
                temperature=opts.temperature,
                max_tokens=opts.max_tokens,
            )
            msg = resp.choices[0].message
            tool_calls: list[dict[str, Any]] = []
            for tc in msg.tool_calls or []:
                args = {}
                raw = getattr(tc.function, "arguments", "{}") or "{}"
                try:
                    args = json.loads(raw)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(
                    {"id": tc.id, "name": tc.function.name, "input": args}
                )
            usage = getattr(resp, "usage", None)
            return LLMResponse(
                text=msg.content or "",
                model=model,
                stop_reason=getattr(resp.choices[0], "finish_reason", None),
                input_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
                output_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
                tool_calls=tool_calls,
            )
        except Exception as exc:
            raise InfrastructureError(
                "Groq tool calling fallo",
                details={"model": model, "error": str(exc)},
            ) from exc


# ---------------------------------------------------------------------------
# Singleton para apps
# ---------------------------------------------------------------------------


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Cliente compartido por la API/agentes. Inicialización lazy."""
    global _client
    if _client is None:
        _client = LLMClient()
        log.info(
            "llm_client.ready",
            offline=_client.is_offline,
            brain=_client._brain_model,
            light=_client._light_model,
        )
    return _client


__all__ = [
    "LLMClient",
    "LLMMessage",
    "LLMOptions",
    "LLMResponse",
    "LLMRole",
    "get_llm_client",
]

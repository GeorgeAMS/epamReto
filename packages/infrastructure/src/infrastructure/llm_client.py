"""Cliente LLM unificado con Groq.

Reglas:
- ``LLMRole.BRAIN`` -> modelo principal para síntesis/respuesta final.
- ``LLMRole.LIGHT`` -> modelo ligero para clasificación/tool-use.
- Streaming real vía SDK Groq.
- ``complete_with_tools`` usa function-calling estilo OpenAI.
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

    El lenguaje del proyecto: cualquier agente pide ``BRAIN`` o ``LIGHT``.
    """

    BRAIN = "brain"
    LIGHT = "light"


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
    snippet = " ".join(prompt.strip().split())[:600]
    return (
        f"[offline:{role.value}:{digest}] "
        "Respuesta determinística -- configura GROQ_API_KEY para activar el LLM real. "
        f"Prompt: {snippet}"
    )


# ---------------------------------------------------------------------------
# Cliente principal
# ---------------------------------------------------------------------------


class LLMClient:
    """Cliente unificado Groq."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        brain_model: str | None = None,
        light_model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key if api_key is not None else settings.groq_api_key
        self._brain_model = brain_model or settings.llm_brain_model
        self._light_model = light_model or settings.llm_light_model
        self._sdk: Any | None = None  # Groq SDK lazy.
        self._last_call = 0.0
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

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_call
        if elapsed < self._min_interval_seconds:
            time.sleep(self._min_interval_seconds - elapsed)
        self._last_call = time.time()

    @rate_limit(min_interval=0.5)
    def invoke(self, messages: list[dict[str, str]], max_tokens: int = 150, temperature: float = 0.3, timeout: int = 3) -> Any:
        """Invoke con rate limiting + timeout."""
        if self.is_offline:
            raise InfrastructureError("Groq API error", details={"error": "offline mode"})
        sdk = self._ensure_sdk()
        model = self._model_for(LLMRole.BRAIN)
        try:
            response = sdk.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response
        except Exception as e:
            raise InfrastructureError("Groq API error", details={"error": str(e), "timeout": timeout}) from e

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

        sdk = self._ensure_sdk()
        self._rate_limit()
        try:
            msgs = self._build_history(prompt, history)
            if opts.system:
                msgs = [{"role": "system", "content": opts.system}, *msgs]
            resp = sdk.chat.completions.create(
                model=model,
                messages=msgs,
                max_tokens=opts.max_tokens,
                temperature=opts.temperature,
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

        En offline tokeniza por carácter el offline_text para que la UI siga
        animándose en demos sin créditos.
        """
        opts = options or LLMOptions()
        model = self._model_for(role)

        if self.is_offline:
            text = _offline_text(prompt, role)
            yield from text  # carácter a carácter: el SSE de la API tokeniza igual
            return

        sdk = self._ensure_sdk()
        self._rate_limit()
        try:
            msgs = self._build_history(prompt, history)
            if opts.system:
                msgs = [{"role": "system", "content": opts.system}, *msgs]
            stream = sdk.chat.completions.create(
                model=model,
                messages=msgs,
                max_tokens=opts.max_tokens,
                temperature=opts.temperature,
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
        """Soporte de function-calling en Groq."""
        opts = options or LLMOptions()
        model = self._model_for(role)

        if self.is_offline:
            return LLMResponse(
                text=_offline_text(prompt, role),
                model=f"{model}:offline",
                tool_calls=[],
            )

        sdk = self._ensure_sdk()
        self._rate_limit()
        msgs = self._build_history(prompt, history)
        if opts.system:
            msgs = [{"role": "system", "content": opts.system}, *msgs]
        try:
            resp = sdk.chat.completions.create(
                model=model,
                messages=msgs,
                tools=self._to_openai_tools(tools),
                tool_choice="auto",
                max_tokens=opts.max_tokens,
                temperature=opts.temperature,
            )
            msg = resp.choices[0].message
            tool_calls: list[dict[str, Any]] = []
            for tc in msg.tool_calls or []:
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
            # Algunos modelos de Groq pueden rechazar tool-calling.
            # Degradamos a completion normal para evitar ruido en classify.
            log.info(
                "llm.tools_fallback_to_complete",
                model=model,
                error=str(exc),
            )
            base = self.complete(prompt, role=role, options=options, history=history)
            return LLMResponse(
                text=base.text,
                model=base.model,
                stop_reason=base.stop_reason,
                input_tokens=base.input_tokens,
                output_tokens=base.output_tokens,
                tool_calls=[],
            )


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

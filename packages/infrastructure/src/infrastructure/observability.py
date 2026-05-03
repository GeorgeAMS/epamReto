"""Wrapper de observabilidad sobre Langfuse.

Si las credenciales no están presentes, las llamadas se vuelven no-ops.
Esto permite correr la app sin Langfuse en local sin código condicional disperso.

Tres herramientas se exportan:
- ``get_langfuse()``       → cliente real o stub.
- ``trace_agent(...)``     → context manager para trazar bloques manuales.
- ``traced(agent_name)``   → decorator que envuelve ``BaseAgent.run`` /
  cualquier callable que reciba un objeto con ``.trace_id`` y registre
  inicio/fin + latencia + outcome en Langfuse + structlog.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any, ParamSpec, TypeVar

from infrastructure.settings import get_settings
from shared.logging import get_logger

log = get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


class _NullLangfuse:
    """Stub que respeta el shape básico del cliente Langfuse."""

    def trace(self, **kwargs: Any) -> _NullSpan:
        return _NullSpan()

    def flush(self) -> None:
        return None


class _NullSpan:
    def span(self, **kwargs: Any) -> _NullSpan:
        return self

    def update(self, **kwargs: Any) -> None:
        return None

    def end(self) -> None:
        return None


_lf: Any = None


def get_langfuse() -> Any:
    """Devuelve cliente Langfuse o stub no-op si no hay credenciales."""
    global _lf
    if _lf is not None:
        return _lf

    settings = get_settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        log.info("langfuse.disabled", reason="missing_credentials")
        _lf = _NullLangfuse()
        return _lf

    try:
        from langfuse import Langfuse  # type: ignore[import-not-found]

        _lf = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        log.info("langfuse.enabled", host=settings.langfuse_host)
    except ImportError:
        log.warning("langfuse.import_failed")
        _lf = _NullLangfuse()
    return _lf


@contextmanager
def trace_agent(
    *,
    agent: str,
    trace_id: str,
    user_query: str | None = None,
) -> Generator[Any, None, None]:
    """Context manager que abre/cierra un span con etiqueta del agente.

    Uso típico::

        with trace_agent(agent="stats_agent", trace_id=tid) as span:
            ...resultado = ...
            span.update(output={"answer": resultado})
    """
    lf = get_langfuse()
    trace = lf.trace(id=trace_id, name=agent, input={"query": user_query})
    span = trace.span(name=agent) if hasattr(trace, "span") else trace
    try:
        yield span
    finally:
        if hasattr(span, "end"):
            span.end()


# ---------------------------------------------------------------------------
# Decorator @traced(agent_name)
# ---------------------------------------------------------------------------


def _extract_trace_id(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """Heurística para sacar trace_id del primer argumento "agent_input".

    Busca, en orden:
    1. ``kwargs["agent_input"].trace_id``
    2. ``kwargs["trace_id"]``
    3. el primer arg posicional (después de self) que tenga ``.trace_id``.
    """
    if "agent_input" in kwargs and hasattr(kwargs["agent_input"], "trace_id"):
        return str(kwargs["agent_input"].trace_id)
    if "trace_id" in kwargs:
        return str(kwargs["trace_id"])
    for arg in args[1:]:  # saltamos self
        if hasattr(arg, "trace_id"):
            return str(arg.trace_id)
    return "no-trace"


def traced(agent_name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator: envuelve ``BaseAgent.run`` (o equivalente) con tracing.

    Combina:
    - **structlog**: emite logs ``agent.start`` / ``agent.end`` con duración.
    - **Langfuse**:  abre/cierra un span etiquetado con ``agent_name`` y
      registra el output cuando es serializable.

    Es seguro de aplicar a métodos sync. Para async se podría extender; en
    Día 1 todos los agentes son sync (calculator y stats fundamentalmente
    determinísticos).

    Ejemplo::

        class StatsAgent(BaseAgent):
            @traced("stats_agent")
            def run(self, agent_input: AgentInput) -> AgentResponse:
                ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            trace_id = _extract_trace_id(args, kwargs)
            started = time.perf_counter()
            log.info("agent.start", agent=agent_name, trace_id=trace_id)
            with trace_agent(agent=agent_name, trace_id=trace_id) as span:
                try:
                    result = func(*args, **kwargs)
                except Exception as exc:
                    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
                    log.warning(
                        "agent.error",
                        agent=agent_name,
                        trace_id=trace_id,
                        elapsed_ms=elapsed_ms,
                        error=str(exc),
                    )
                    if hasattr(span, "update"):
                        span.update(level="ERROR", status_message=str(exc))
                    raise
                elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
                log.info(
                    "agent.end",
                    agent=agent_name,
                    trace_id=trace_id,
                    elapsed_ms=elapsed_ms,
                )
                if hasattr(span, "update"):
                    output_payload: Any = result
                    # Si el resultado es Pydantic, lo serializamos.
                    if hasattr(result, "model_dump"):
                        output_payload = result.model_dump()  # type: ignore[union-attr]
                    span.update(output=output_payload)
                return result

        return wrapper

    return decorator


__all__ = ["get_langfuse", "trace_agent", "traced"]

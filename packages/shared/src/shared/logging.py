"""Logging estructurado con structlog + propagación de ``trace_id``.

Convenciones:
- ``configure_logging`` se llama una sola vez al arrancar la API/CLIs.
- ``get_logger(__name__)`` devuelve un ``BoundLogger`` que respeta el
  contexto bindeado (trace_id, agent, etc.).
- ``bind_trace_id`` es un context manager que ata un trace_id al contexto
  durante la duración de un request/handler. Si no llega trace_id se genera
  uno (12 chars hex) — mismo formato que usa ``AgentInput``.

Ejemplo::

    from shared.logging import configure_logging, get_logger, bind_trace_id

    configure_logging(level="INFO", json_logs=False)
    log = get_logger(__name__)

    with bind_trace_id(req.headers.get("x-trace-id")) as tid:
        log.info("chat.request", query=req.query)
        # ...todo lo logueado dentro del with lleva trace_id=tid.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

import structlog
from structlog.contextvars import bind_contextvars, unbind_contextvars
from structlog.stdlib import BoundLogger

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

_CONFIGURED = False


def configure_logging(*, level: str = "INFO", json_logs: bool | None = None) -> None:
    """Configura structlog + logging stdlib de forma idempotente.

    Args:
        level: Uno de DEBUG, INFO, WARNING, ERROR, CRITICAL (case-insensitive).
        json_logs: Si ``True`` emite JSON (recomendado producción/Langfuse).
            Si ``None``, lee ``LOG_FORMAT`` del entorno (``json`` → True,
            cualquier otro → False = consola coloreada).
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_no = getattr(logging, level.upper(), logging.INFO)

    if json_logs is None:
        json_logs = os.environ.get("LOG_FORMAT", "console").lower() == "json"

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
    ]

    renderer: Any
    if json_logs:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level_no),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=level_no,
        force=True,
    )

    _CONFIGURED = True


def get_logger(name: str | None = None) -> BoundLogger:
    """Logger estructurado bindeado al contexto activo.

    Usar ``get_logger(__name__)`` en cada módulo. Si nadie llamó
    ``configure_logging`` antes, lo hace con defaults razonables.
    """
    if not _CONFIGURED:
        configure_logging()
    return structlog.get_logger(name)  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Trace id propagation
# ---------------------------------------------------------------------------


def _new_trace_id() -> str:
    """12 chars hex es lo bastante único y compacto para humans+UI."""
    return uuid4().hex[:12]


@contextmanager
def bind_trace_id(trace_id: str | None) -> Generator[str, None, None]:
    """Bind ``trace_id`` al contexto de structlog y devuélvelo al caller.

    Si ``trace_id`` viene ``None`` se genera uno fresco. El valor real (sea
    nuevo o reusado) se yieldea para que el caller lo propague (header HTTP,
    Langfuse, etc.).
    """
    tid = trace_id or _new_trace_id()
    bind_contextvars(trace_id=tid)
    try:
        yield tid
    finally:
        unbind_contextvars("trace_id")


__all__ = [
    "bind_trace_id",
    "configure_logging",
    "get_logger",
]

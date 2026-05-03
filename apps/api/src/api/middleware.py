"""Middleware HTTP — trace_id correlation + structured request logging.

Reglas del proyecto:
- Cada request lleva un ``X-Trace-Id`` (lo crea el middleware si no viene).
- El header se propaga en la respuesta para que el cliente lo cite.
- ``shared.logging.bind_trace_id`` lo expone como contextvar para que cualquier
  ``get_logger(...)`` dentro del request lo emita automáticamente.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from shared.logging import bind_trace_id, get_logger

log = get_logger(__name__)

_TRACE_HEADER = "X-Trace-Id"


class TraceIdMiddleware(BaseHTTPMiddleware):
    """Garantiza un ``trace_id`` por request y lo loguea estructurado."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get(_TRACE_HEADER)
        trace_id = incoming or uuid4().hex[:12]
        request.state.trace_id = trace_id

        start = time.perf_counter()
        with bind_trace_id(trace_id):
            log.info(
                "http.request",
                method=request.method,
                path=request.url.path,
                trace_id=trace_id,
            )
            try:
                response = await call_next(request)
            except Exception as exc:
                log.error(
                    "http.error",
                    method=request.method,
                    path=request.url.path,
                    error=str(exc),
                    elapsed_ms=round((time.perf_counter() - start) * 1000, 2),
                )
                raise
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            log.info(
                "http.response",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                elapsed_ms=elapsed_ms,
            )
            response.headers[_TRACE_HEADER] = trace_id
            return response


__all__ = ["TraceIdMiddleware"]

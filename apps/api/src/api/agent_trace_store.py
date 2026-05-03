"""Timeline en memoria para el panel «Agent Trace» del frontend.

Cada evento ligero (intent, agente, done) se anexa por ``conversation_id``.
No sustituye a Langfuse: cuando las credenciales estén configuradas, el UI
puede enlazar spans ricos; este store garantiza datos incluso con Langfuse
desactivado.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class TraceTimelineEntry:
    """Una fila de la línea de tiempo mostrada en el frontend."""

    ts_iso: str
    trace_id: str
    kind: str
    detail: dict[str, Any]


class AgentTraceStore:
    """Store thread-safe: conversación → lista cronológica de eventos."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._by_conversation: dict[str, list[TraceTimelineEntry]] = defaultdict(list)

    def record(
        self,
        *,
        conversation_id: str,
        trace_id: str,
        kind: str,
        detail: dict[str, Any],
    ) -> None:
        entry = TraceTimelineEntry(
            ts_iso=datetime.now(UTC).isoformat(timespec="milliseconds"),
            trace_id=trace_id,
            kind=kind,
            detail=detail,
        )
        with self._lock:
            self._by_conversation[conversation_id].append(entry)

    def timeline(self, conversation_id: str) -> list[TraceTimelineEntry]:
        with self._lock:
            return list(self._by_conversation.get(conversation_id, []))

    def clear_conversation(self, conversation_id: str) -> None:
        with self._lock:
            self._by_conversation.pop(conversation_id, None)


__all__ = ["AgentTraceStore", "TraceTimelineEntry"]

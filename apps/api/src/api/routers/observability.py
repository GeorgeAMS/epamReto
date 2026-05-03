"""Router /traces — vista de telemetría para el panel "Agent Trace".

Día 1: leemos del store en memoria y exponemos turnos + timestamps. Día 5
añadiremos la integración Langfuse: ``GET /traces/{conversation_id}/spans``
con la lista de spans (orchestrator, classify, dispatch, sub-agentes, verify,
synthesize) tal como Langfuse los persiste.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.agent_trace_store import AgentTraceStore
from api.conversations_store import ConversationStore
from api.dependencies import get_agent_trace, get_conversations
from infrastructure.settings import get_settings
from shared.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/traces", tags=["observability"])


class TraceTurnDTO(BaseModel):
    id: str
    role: str
    confidence: str
    citation_count: int
    created_at: datetime


class TimelineEventDTO(BaseModel):
    ts_iso: str
    trace_id: str
    kind: str
    detail: dict[str, Any]


class TraceDTO(BaseModel):
    conversation_id: str
    turn_count: int
    turns: list[TraceTurnDTO]
    langfuse_enabled: bool
    langfuse_url: str | None
    timeline: list[TimelineEventDTO]


@router.get("/{conversation_id}", response_model=TraceDTO)
def get_trace(
    conversation_id: str,
    conversations: ConversationStore = Depends(get_conversations),
    agent_trace: AgentTraceStore = Depends(get_agent_trace),
) -> TraceDTO:
    conv = conversations.get(conversation_id)
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversación '{conversation_id}' no encontrada",
        )
    settings = get_settings()
    timeline_raw = agent_trace.timeline(conversation_id)
    return TraceDTO(
        conversation_id=conv.id,
        turn_count=len(conv.turns),
        turns=[
            TraceTurnDTO(
                id=t.id,
                role=t.role.value,
                confidence=t.confidence.value,
                citation_count=len(t.citations),
                created_at=t.created_at,
            )
            for t in conv.turns
        ],
        langfuse_enabled=bool(
            settings.langfuse_public_key and settings.langfuse_secret_key
        ),
        langfuse_url=settings.langfuse_host or None,
        timeline=[
            TimelineEventDTO(
                ts_iso=e.ts_iso,
                trace_id=e.trace_id,
                kind=e.kind,
                detail=e.detail,
            )
            for e in timeline_raw
        ],
    )


__all__ = ["router"]

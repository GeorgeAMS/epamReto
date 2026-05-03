"""Router /conversations — CRUD en memoria.

Este router es la fuente de verdad para el frontend cuando renderiza el
historial. Cada turno incluye sus citas, confidence_level y timestamps.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from api.agent_trace_store import AgentTraceStore
from api.conversations_store import ConversationStore
from api.dependencies import get_agent_trace, get_conversations
from domain.conversation.entities import Conversation, Turn
from shared.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


class CitationDTO(BaseModel):
    id: str
    title: str
    url: str | None = None
    snippet: str | None = None
    kind: str = "unknown"


class TurnDTO(BaseModel):
    id: str
    role: str
    content: str
    confidence: str
    citations: list[CitationDTO]
    mentioned_pokemon: list[str]
    mentioned_moves: list[str]
    created_at: datetime


class ConversationDTO(BaseModel):
    id: str
    created_at: datetime
    turns: list[TurnDTO]


class ConversationSummary(BaseModel):
    id: str
    created_at: datetime
    turn_count: int
    last_user_query: str | None


def _turn_to_dto(turn: Turn) -> TurnDTO:
    return TurnDTO(
        id=turn.id,
        role=turn.role.value,
        content=turn.content,
        confidence=turn.confidence.value,
        citations=[
            CitationDTO(
                id=c.id,
                title=c.title,
                url=c.url,
                snippet=c.snippet,
                kind=c.kind,
            )
            for c in turn.citations
        ],
        mentioned_pokemon=list(turn.mentioned_pokemon),
        mentioned_moves=list(turn.mentioned_moves),
        created_at=turn.created_at,
    )


def _conv_to_dto(conv: Conversation) -> ConversationDTO:
    return ConversationDTO(
        id=conv.id,
        created_at=conv.created_at,
        turns=[_turn_to_dto(t) for t in conv.turns],
    )


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    conversations: ConversationStore = Depends(get_conversations),
) -> list[ConversationSummary]:
    summaries: list[ConversationSummary] = []
    for conv in conversations.list():
        last_user = conv.latest_user_turn()
        summaries.append(
            ConversationSummary(
                id=conv.id,
                created_at=conv.created_at,
                turn_count=len(conv.turns),
                last_user_query=last_user.content if last_user else None,
            )
        )
    summaries.sort(key=lambda s: s.created_at, reverse=True)
    return summaries


@router.get("/{conversation_id}/turns", response_model=list[TurnDTO])
def list_turns(
    conversation_id: str,
    conversations: ConversationStore = Depends(get_conversations),
) -> list[TurnDTO]:
    conv = conversations.get(conversation_id)
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversación '{conversation_id}' no encontrada",
        )
    return [_turn_to_dto(t) for t in conv.turns]


@router.get("/{conversation_id}", response_model=ConversationDTO)
def get_conversation(
    conversation_id: str,
    conversations: ConversationStore = Depends(get_conversations),
) -> ConversationDTO:
    conv = conversations.get(conversation_id)
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversación '{conversation_id}' no encontrada",
        )
    return _conv_to_dto(conv)


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_conversation(
    conversation_id: str,
    conversations: ConversationStore = Depends(get_conversations),
    agent_trace: AgentTraceStore = Depends(get_agent_trace),
) -> Response:
    if not conversations.delete(conversation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversación '{conversation_id}' no encontrada",
        )
    agent_trace.clear_conversation(conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=ConversationDTO, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conversations: ConversationStore = Depends(get_conversations),
) -> ConversationDTO:
    return _conv_to_dto(conversations.create())


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_all_conversations(
    conversations: ConversationStore = Depends(get_conversations),
    agent_trace: AgentTraceStore = Depends(get_agent_trace),
) -> Response:
    """Helper de desarrollo — borra todo el store. **No** lo expongas en prod."""
    ids = [c.id for c in conversations.list()]
    conversations.clear()
    for cid in ids:
        agent_trace.clear_conversation(cid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]


# Re-export de tipos para tests/clients que quieran tipar la respuesta sin
# importar desde el router (evita circular).
__all__ += ["CitationDTO", "ConversationDTO", "ConversationSummary", "TurnDTO"]


def _re_export() -> dict[str, Any]:  # pragma: no cover - sólo para debug interactivo
    return {
        "ConversationDTO": ConversationDTO,
        "TurnDTO": TurnDTO,
        "CitationDTO": CitationDTO,
    }

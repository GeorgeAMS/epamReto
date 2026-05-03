"""Router /chat — endpoint síncrono + endpoint SSE con streaming real.

- ``POST /chat``         → ejecuta el grafo y devuelve la respuesta completa.
- ``POST /chat/stream``  → SSE con eventos ``intent | agent | token | done``
  generados por ``Orchestrator.handle_stream`` (tokens reales de Anthropic
  cuando hay API key, hash determinístico tokenizado en offline).

Ambos endpoints aceptan ``conversation_id`` opcional. Si llega un id existente
se reutiliza; si no, se crea uno nuevo. Cada request añade un ``Turn`` user y
otro assistant a la conversación correspondiente.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from agents.base import AgentResponse
from agents.orchestrator import Orchestrator
from api.agent_trace_store import AgentTraceStore
from api.conversations_store import ConversationStore
from api.dependencies import (
    get_agent_trace,
    get_conversations,
    get_orchestrator,
    get_trace_id,
)
from shared.logging import get_logger
from shared.types import TraceId

log = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None
    # Payload estructurado para el orchestrator (p. ej. calculator_request, team).
    context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    agent: str
    content: str
    confidence: float
    confidence_level: str
    sources: list[dict[str, Any]]
    data: dict[str, Any]
    trace_id: str
    conversation_id: str


def _serialize(response: AgentResponse, *, conversation_id: str) -> ChatResponse:
    return ChatResponse(
        agent=response.agent,
        content=response.content,
        confidence=response.confidence,
        confidence_level=response.confidence_level.value,
        sources=[s.model_dump(mode="json") for s in response.sources],
        data=response.data,
        trace_id=str(response.trace_id),
        conversation_id=conversation_id,
    )


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    conversations: ConversationStore = Depends(get_conversations),
    agent_trace: AgentTraceStore = Depends(get_agent_trace),
    trace_id: str = Depends(get_trace_id),
) -> ChatResponse:
    """Ejecuta el grafo de agentes de forma bloqueante y devuelve la respuesta."""
    conv = conversations.get_or_create(req.conversation_id)
    conversations.append_user_turn(conv.id, req.query)

    log.info(
        "chat.invoke",
        query=req.query,
        conversation_id=conv.id,
        trace_id=trace_id,
    )
    # El orchestrator es sync (LangGraph compilado sync). Lo despachamos a un
    # thread para no bloquear el event loop de FastAPI.
    ctx = req.context if req.context else None
    response = await asyncio.to_thread(
        orchestrator.handle,
        req.query,
        trace_id=TraceId(trace_id) if trace_id else None,
        context=ctx,
    )
    agent_trace.record(
        conversation_id=conv.id,
        trace_id=trace_id,
        kind="chat_sync",
        detail={
            "agent": response.agent,
            "confidence": response.confidence,
            "confidence_level": response.confidence_level.value,
        },
    )
    conversations.append_assistant_turn(conv.id, response)
    return _serialize(response, conversation_id=conv.id)


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    request: Request,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    conversations: ConversationStore = Depends(get_conversations),
    agent_trace: AgentTraceStore = Depends(get_agent_trace),
    trace_id: str = Depends(get_trace_id),
) -> EventSourceResponse:
    """SSE con streaming real de Anthropic (token-a-token).

    Eventos emitidos:
    - ``intent``  → ``{intent, entities}`` después del clasificador Haiku.
    - ``agent``   → uno por sub-agente con ``{agent, confidence, sources}``.
    - ``token``   → cada delta de texto del Synthesizer (Sonnet streaming).
    - ``done``    → ``{trace_id, confidence, confidence_level, sources, data}``.
    """
    conv = conversations.get_or_create(req.conversation_id)
    user_turn = conversations.append_user_turn(conv.id, req.query)
    log.info(
        "chat.stream.invoke",
        query=req.query,
        conversation_id=conv.id,
        trace_id=trace_id,
        user_turn=user_turn.id,
    )

    final_holder: dict[str, AgentResponse] = {}
    accumulated_tokens: list[str] = []
    ctx = req.context if req.context else None

    async def event_gen() -> AsyncIterator[dict[str, Any]]:
        loop = asyncio.get_running_loop()
        sync_iter = orchestrator.handle_stream(
            req.query,
            trace_id=TraceId(trace_id) if trace_id else None,
            context=ctx,
        )
        sentinel: object = object()
        last_event: dict[str, Any] | None = None

        # Bridge sync → async sin bloquear el event loop: cada `next()` corre
        # en el threadpool default de asyncio.
        while True:
            if await request.is_disconnected():
                log.warning("chat.stream.client_disconnected", trace_id=trace_id)
                break
            event = await loop.run_in_executor(None, lambda: next(sync_iter, sentinel))
            if event is sentinel:
                break
            assert isinstance(event, dict)
            last_event = event
            event_type = event.get("event")
            if event_type == "intent":
                try:
                    agent_trace.record(
                        conversation_id=conv.id,
                        trace_id=trace_id,
                        kind="intent",
                        detail=json.loads(str(event.get("data", "{}"))),
                    )
                except (json.JSONDecodeError, TypeError):
                    agent_trace.record(
                        conversation_id=conv.id,
                        trace_id=trace_id,
                        kind="intent",
                        detail={"raw": str(event.get("data"))},
                    )
            elif event_type == "agent":
                try:
                    agent_trace.record(
                        conversation_id=conv.id,
                        trace_id=trace_id,
                        kind="agent",
                        detail=json.loads(str(event.get("data", "{}"))),
                    )
                except (json.JSONDecodeError, TypeError):
                    agent_trace.record(
                        conversation_id=conv.id,
                        trace_id=trace_id,
                        kind="agent",
                        detail={"raw": str(event.get("data"))},
                    )
            elif event_type == "done":
                try:
                    agent_trace.record(
                        conversation_id=conv.id,
                        trace_id=trace_id,
                        kind="done",
                        detail=json.loads(str(event.get("data", "{}"))),
                    )
                except (json.JSONDecodeError, TypeError):
                    agent_trace.record(
                        conversation_id=conv.id,
                        trace_id=trace_id,
                        kind="done",
                        detail={"raw": str(event.get("data"))},
                    )
            if event_type == "token":
                accumulated_tokens.append(str(event.get("data", "")))
            yield event

        # Persistimos el assistant turn al final del stream.
        if accumulated_tokens and last_event and last_event.get("event") == "done":
            content = "".join(accumulated_tokens)
            data = last_event.get("data")
            sources_json: list[dict[str, Any]] = []
            confidence = 0.0
            if isinstance(data, str):
                try:
                    payload = json.loads(data)
                    sources_json = payload.get("sources", [])
                    confidence = float(payload.get("confidence", 0.0))
                except (ValueError, TypeError):
                    pass
            # Guardamos un turn assistant ligero (sin re-llamar al graph).
            from agents.base import AgentResponse as _AR
            from shared.types import Source as _Src

            sources = [
                _Src.model_validate(s) for s in sources_json if isinstance(s, dict)
            ]
            final_holder["response"] = _AR(
                agent="synthesizer",
                content=content,
                sources=sources,
                confidence=confidence,
                trace_id=TraceId(trace_id) if trace_id else TraceId("unknown"),
            )
            conversations.append_assistant_turn(conv.id, final_holder["response"])

    return EventSourceResponse(event_gen())


__all__ = ["router"]

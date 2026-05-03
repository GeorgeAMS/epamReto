"""Inyección de dependencias para FastAPI.

Centralizamos los singletons (orchestrator, reporter, conversation store) y
los exponemos como ``Depends`` para que los routers no importen ``app.state``
directamente — eso facilita testing (sustituir con un fake en una fixture).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import cast

from fastapi import Depends, Request

from agents.orchestrator import Orchestrator
from agents.reporter_agent import ReporterAgent
from api.agent_trace_store import AgentTraceStore
from api.conversations_store import ConversationStore


def get_orchestrator(request: Request) -> Orchestrator:
    return cast(Orchestrator, request.app.state.orchestrator)


def get_reporter(request: Request) -> ReporterAgent:
    return cast(ReporterAgent, request.app.state.reporter)


def get_conversations(request: Request) -> ConversationStore:
    return cast(ConversationStore, request.app.state.conversations)


def get_agent_trace(request: Request) -> AgentTraceStore:
    return cast(AgentTraceStore, request.app.state.agent_trace)


def get_trace_id(request: Request) -> str:
    """Devuelve el ``trace_id`` enlazado al request por el middleware."""
    return cast(str, getattr(request.state, "trace_id", ""))


# Aliases tipados para los routers (evita anotaciones repetidas).
OrchestratorDep = Depends(get_orchestrator)
ReporterDep = Depends(get_reporter)
ConversationsDep = Depends(get_conversations)
TraceIdDep = Depends(get_trace_id)
AgentTraceDep = Depends(get_agent_trace)


def iter_dependencies() -> Iterator[str]:
    """Iterador puramente informativo — útil para self-doc del router."""
    yield from ("orchestrator", "reporter", "conversations")


__all__ = [
    "AgentTraceDep",
    "ConversationsDep",
    "OrchestratorDep",
    "ReporterDep",
    "TraceIdDep",
    "get_agent_trace",
    "get_conversations",
    "get_orchestrator",
    "get_reporter",
    "get_trace_id",
    "iter_dependencies",
]

"""FastAPI app — entrypoint HTTP de Pokédex Arcana.

Endpoints (Día 2):
- ``GET  /health``                          — diagnóstico de servicios.
- ``POST /chat``                            — síncrono, ejecuta el grafo.
- ``POST /chat/stream``                     — SSE con streaming real Anthropic.
- ``GET/POST/DELETE /conversations``        — CRUD en memoria.
- ``POST /reports/generate``                — produce Markdown + PDF.
- ``GET  /reports/file``                    — descarga MD/PDF generado.
- ``GET  /traces/{conversation_id}``        — telemetría para "Agent Trace".

Inyección: el ``lifespan`` instancia los singletons (orchestrator, reporter,
conversation store) y los expone vía ``app.state``. Los routers consumen estos
singletons mediante ``Depends`` (``api.dependencies``), nunca tocando
``app.state`` directamente.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.orchestrator import Orchestrator
from agents.reporter_agent import ReporterAgent
from api.agent_trace_store import AgentTraceStore
from api.conversations_store import ConversationStore
from api.middleware import TraceIdMiddleware
from api.routers import chat, compare, conversations, observability, pokedex, reports, saved_teams, teams
from infrastructure.settings import get_settings
from shared.logging import configure_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(level=settings.api_log_level, json_logs=(settings.env != "dev"))
    settings.ensure_data_dirs()

    app.state.orchestrator = Orchestrator()
    app.state.reporter = ReporterAgent(output_dir=settings.reports_dir)
    app.state.conversations = ConversationStore()
    app.state.agent_trace = AgentTraceStore()

    log.info(
        "api.startup",
        env=settings.env,
        port=settings.api_port,
        reports_dir=str(settings.reports_dir),
    )
    try:
        yield
    finally:
        log.info("api.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Pokédex Arcana API",
        version="0.2.0",
        description=(
            "Sistema multi-agente para preguntas verificables del universo Pokémon. "
            "Streaming real Anthropic, citas inline, reporter PDF, observabilidad."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(TraceIdMiddleware)
    # CORS must be registered before routes for frontend preflight requests.
    cors_origins = list(dict.fromkeys([*settings.cors_origins_list, "http://localhost:3000", "http://127.0.0.1:3000"]))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Trace-Id"],
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        s = get_settings()
        return {
            "status": "ok",
            "env": s.env,
            "version": app.version,
            "services": {
                "groq_configured": bool(s.groq_api_key),
                "ollama_base_url": s.ollama_base_url,
                "qdrant_url": s.qdrant_url,
                "langfuse_enabled": bool(s.langfuse_public_key and s.langfuse_secret_key),
            },
        }

    app.include_router(chat.router)
    app.include_router(conversations.router)
    app.include_router(pokedex.router)
    app.include_router(reports.router)
    app.include_router(observability.router)
    app.include_router(teams.router)
    app.include_router(compare.router)
    app.include_router(saved_teams.router)

    return app


app = create_app()

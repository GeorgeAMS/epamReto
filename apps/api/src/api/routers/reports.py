"""Router /reports — genera Markdown/PDF a partir de una query o conversación.

Modos soportados (cuerpo JSON):

1. ``{"query": "...", "conversation_id"?: "..."}`` → re-ejecuta el orchestrator
   sobre la query y produce el reporte. Cuando hay ``conversation_id`` registramos
   un nuevo turno con la respuesta para mantener el historial coherente.
2. ``{"conversation_id": "..."}`` (sin query) → toma el último turno user de la
   conversación, lo re-ejecuta y reporta. Útil para "Generate Report" cuando el
   usuario ya conversó.

Devuelve metadata con ``md_path`` y ``pdf_path``. El cliente luego baja el PDF
con ``GET /reports/file?path=...`` (helper que sirve el archivo del filesystem).
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from agents.orchestrator import Orchestrator
from agents.reporter_agent import ReporterAgent
from api.conversations_store import ConversationStore
from api.dependencies import (
    get_conversations,
    get_orchestrator,
    get_reporter,
    get_trace_id,
)
from shared.logging import get_logger
from shared.types import TraceId

log = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


class ReportRequest(BaseModel):
    query: str | None = Field(
        default=None,
        description="Query a reportar. Si va vacía, se toma del último turn user.",
    )
    conversation_id: str | None = None
    context: dict[str, Any] | None = Field(
        default=None,
        description="Contexto opcional para el orchestrator (calculator_request, etc.).",
    )


class ReportResponse(BaseModel):
    md_path: str
    pdf_path: str | None
    trace_id: str
    confidence: float
    confidence_level: str
    sources: list[dict[str, Any]]


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    req: ReportRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
    reporter: ReporterAgent = Depends(get_reporter),
    conversations: ConversationStore = Depends(get_conversations),
    trace_id: str = Depends(get_trace_id),
) -> ReportResponse:
    query = req.query
    if not query and req.conversation_id:
        conv = conversations.get(req.conversation_id)
        if conv is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversación '{req.conversation_id}' no encontrada",
            )
        last_user = conv.latest_user_turn()
        if last_user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La conversación no tiene mensajes del usuario",
            )
        query = last_user.content

    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes enviar `query` o `conversation_id` con turnos",
        )

    log.info("reports.generate", query=query, trace_id=trace_id)
    response = await asyncio.to_thread(
        orchestrator.handle,
        query,
        trace_id=TraceId(trace_id) if trace_id else None,
        context=req.context if req.context else None,
    )
    data = await asyncio.to_thread(
        reporter.generate,
        query=query,
        synthesis=response,
        trace_id=trace_id or None,
    )

    return ReportResponse(
        md_path=str(data.get("md_path", "")),
        pdf_path=str(data["pdf_path"]) if data.get("pdf_path") else None,
        trace_id=str(response.trace_id),
        confidence=response.confidence,
        confidence_level=response.confidence_level.value,
        sources=[s.model_dump(mode="json") for s in response.sources],
    )


@router.get("/file")
def download_file(
    path: str = Query(..., description="Ruta absoluta o relativa devuelta por /generate"),
    reporter: ReporterAgent = Depends(get_reporter),
) -> FileResponse:
    """Sirve archivos generados (PDF/MD).

    Por seguridad sólo permitimos descargar archivos cuya ruta resuelta caiga
    bajo el ``output_dir`` configurado del reporter.
    """
    target = Path(path).resolve()
    output_dir = Path(reporter._output_dir).resolve()
    try:
        target.relative_to(output_dir)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La ruta solicitada está fuera del directorio de reportes",
        ) from exc
    if not target.exists() or not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Archivo no encontrado: {target.name}",
        )

    media_type = "application/pdf" if target.suffix == ".pdf" else "text/markdown"
    return FileResponse(
        path=str(target),
        media_type=media_type,
        filename=os.path.basename(target),
    )


__all__ = ["router"]

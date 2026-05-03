"""Reporter — convierte la respuesta sintetizada en Markdown rico + PDF.

Pipeline:
1. Construye un Markdown estructurado: portada con la query, cuerpo de la
   respuesta del synthesizer, sección de fuentes citadas, anexo con datos
   estructurados (cálculos, coberturas).
2. Convierte a HTML con ``markdown_it_py``.
3. Renderiza PDF con ``weasyprint`` aplicando un CSS oscuro tipo Pokédex.
4. Guarda en ``reports/{trace_id}.pdf`` y devuelve ``AgentResponse`` con
   ``data["pdf_path"]`` para que la API lo sirva.

Si ``weasyprint`` falla (e.g., GTK ausente en Windows), caemos a guardar
solo el ``.md`` para que la demo no se rompa.
"""

from __future__ import annotations

import json
import textwrap
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agents.base import AgentInput, AgentResponse, BaseAgent
from infrastructure.observability import traced
from shared.logging import get_logger

log = get_logger(__name__)

_REPORT_CSS = """
@page { size: A4; margin: 18mm; }
body {
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    background: #0F1117;
    color: #E6E6E6;
    line-height: 1.5;
}
h1 { color: #FFD700; border-bottom: 2px solid #3B4CCA; padding-bottom: 4px; }
h2 { color: #FFD700; margin-top: 1.6em; }
h3 { color: #B5C0FF; }
code, pre {
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    background: #1A1D26; color: #F0F0F0;
    padding: 2px 4px; border-radius: 3px;
}
pre { padding: 8px 12px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; }
th, td { border: 1px solid #2C3140; padding: 6px 10px; text-align: left; }
th { background: #1A1D26; }
.cite { color: #FFD700; font-weight: bold; }
.confidence-verified { color: #4ADE80; }
.confidence-partial { color: #FACC15; }
.confidence-contradiction { color: #F87171; }
"""


class ReporterAgent(BaseAgent):
    """Genera Markdown + PDF a partir de un ``AgentResponse`` final."""

    name = "reporter_agent"

    def __init__(self, *, output_dir: str | Path = "reports") -> None:
        super().__init__(name=self.name)
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    @traced("reporter_agent")
    def run(self, agent_input: AgentInput) -> AgentResponse:
        synthesis = agent_input.context.get("final_response")
        if not isinstance(synthesis, AgentResponse):
            return AgentResponse(
                agent=self.name,
                content="No hay respuesta sintetizada en el contexto para reportar.",
                confidence=0.0,
                trace_id=agent_input.trace_id,
            )

        md = self._render_markdown(agent_input.query, synthesis)
        md_path = self._output_dir / f"{agent_input.trace_id}.md"
        md_path.write_text(md, encoding="utf-8")

        pdf_path: Path | None = None
        try:
            pdf_path = self._render_pdf(md, trace_id=agent_input.trace_id)
        except Exception as exc:  # pragma: no cover - depende de GTK/weasyprint local
            log.warning(
                "reporter.pdf_failed",
                error=str(exc),
                hint="weasyprint requiere GTK en Windows; fallback a .md",
            )

        message = (
            f"Reporte generado en `{md_path}`"
            + (f" y PDF en `{pdf_path}`." if pdf_path else " (PDF no disponible — solo .md).")
        )

        return AgentResponse(
            agent=self.name,
            content=message,
            sources=synthesis.sources,
            confidence=synthesis.confidence,
            data={
                "md_path": str(md_path),
                "pdf_path": str(pdf_path) if pdf_path else None,
                "synthesis_agent": synthesis.agent,
            },
            trace_id=agent_input.trace_id,
        )

    # --- helpers ---------------------------------------------------------

    @staticmethod
    def _render_markdown(query: str, synthesis: AgentResponse) -> str:
        sources_md = "\n".join(
            f"[{i + 1}] **{s.title}** — {s.url or '(sin URL)'}"
            for i, s in enumerate(synthesis.sources)
        ) or "_(sin fuentes)_"

        sub_outputs = synthesis.data.get("intent_outputs") or []
        anexo = ""
        if sub_outputs:
            blocks: list[str] = []
            for o in sub_outputs:
                data_str = json.dumps(o.get("data", {}), ensure_ascii=False, indent=2)
                blocks.append(
                    f"### {o.get('agent', '?')}\n"
                    f"- confidence: `{o.get('confidence', 0)}`\n"
                    f"- payload:\n```\n{data_str}\n```"
                )
            anexo = "\n\n## Anexo — outputs de sub-agentes\n\n" + "\n\n".join(blocks)

        confidence_label = synthesis.confidence_level.value
        timestamp = datetime.now(UTC).isoformat(timespec="seconds")

        return textwrap.dedent(
            f"""\
            # POKÉDEX ARCANA — Reporte

            **Query:** {query}
            **Trace:** `{synthesis.trace_id}`
            **Confidence:** `{confidence_label}` ({synthesis.confidence:.2f})
            **Generado:** {timestamp}

            ---

            ## Respuesta

            {synthesis.content}

            ## Fuentes

            {sources_md}
            {anexo}
            """
        )

    def _render_pdf(self, markdown: str, *, trace_id: str) -> Path:
        from markdown_it import MarkdownIt
        from weasyprint import HTML

        md = MarkdownIt("commonmark", {"html": False}).enable("table")
        html_body = md.render(markdown)
        html_doc = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<style>{_REPORT_CSS}</style></head><body>{html_body}</body></html>"
        )
        pdf_path = self._output_dir / f"{trace_id}.pdf"
        HTML(string=html_doc).write_pdf(str(pdf_path))
        return pdf_path

    # Helper público para que la API/CLI puedan invocar sin pasar por context.
    def generate(
        self,
        *,
        query: str,
        synthesis: AgentResponse,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        ai = AgentInput(
            query=query,
            trace_id=trace_id or synthesis.trace_id,  # type: ignore[arg-type]
            context={"final_response": synthesis},
        )
        result = self.run(ai)
        return result.data


__all__ = ["ReporterAgent"]

"""Tests del ReporterAgent — generación de Markdown (PDF opcional).

El render PDF requiere weasyprint con GTK; en Windows es frágil de testear.
Validamos:
1. Que se genera un .md con el contenido esperado.
2. Que ``run`` sin synthesis devuelve confidence 0.
3. Que ``generate(...)`` (helper público) funciona end-to-end.
"""

from __future__ import annotations

from pathlib import Path

from agents.base import AgentInput, AgentResponse
from agents.reporter_agent import ReporterAgent
from shared.types import Source


def _synthesis_response() -> AgentResponse:
    return AgentResponse(
        agent="synthesizer",
        content="**Garchomp** es un Dragón/Tierra con 600 BST. [1]",
        sources=[
            Source(
                id="src1",
                title="PokéAPI Garchomp",
                url="https://pokeapi.co/api/v2/pokemon/garchomp",
                kind="dataset",
            ),
        ],
        confidence=0.9,
        trace_id="rep-1",
        data={
            "intent_outputs": [
                {
                    "agent": "stats_agent",
                    "confidence": 0.9,
                    "data": {"name": "Garchomp", "bst": 600},
                }
            ],
        },
    )


def test_reporter_run_without_synthesis_returns_zero(tmp_path: Path) -> None:
    reporter = ReporterAgent(output_dir=tmp_path)
    result = reporter.run(AgentInput(query="?"))
    assert result.confidence == 0.0


def test_reporter_writes_markdown(tmp_path: Path) -> None:
    reporter = ReporterAgent(output_dir=tmp_path)
    synth = _synthesis_response()
    ai = AgentInput(
        query="¿Qué tipos tiene Garchomp?",
        trace_id="rep-1",  # type: ignore[arg-type]
        context={"final_response": synth},
    )
    result = reporter.run(ai)

    md_path = Path(result.data["md_path"])
    assert md_path.exists()
    content = md_path.read_text(encoding="utf-8")

    assert "POKÉDEX ARCANA" in content
    assert "Garchomp" in content
    assert "[1]" in content  # cita renderizada
    assert "stats_agent" in content  # anexo


def test_reporter_generate_helper_returns_paths(tmp_path: Path) -> None:
    reporter = ReporterAgent(output_dir=tmp_path)
    synth = _synthesis_response()
    data = reporter.generate(query="test", synthesis=synth)
    assert "md_path" in data
    assert Path(data["md_path"]).exists()

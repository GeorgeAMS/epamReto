"""Tests del Synthesizer: builder de citas y modo offline."""

from __future__ import annotations

from agents.base import AgentInput, AgentResponse
from agents.synthesizer import Synthesizer, _build_synthesis_prompt
from infrastructure.llm_client import LLMClient
from shared.types import Source


def _resp(agent: str, sources: list[Source], conf: float = 0.7) -> AgentResponse:
    return AgentResponse(
        agent=agent,
        content=f"Output del {agent}.",
        sources=sources,
        confidence=conf,
        trace_id="trace-test",
    )


def test_build_prompt_dedupes_and_renumbers_sources() -> None:
    """Si dos agentes citan la misma fuente, debe aparecer una sola vez en [1]."""
    src_a = Source(id="src-a", title="A", url="https://a.example", kind="bulbapedia")
    src_b = Source(id="src-b", title="B", url="https://b.example", kind="smogon")

    out1 = _resp("stats_agent", [src_a])
    out2 = _resp("lore_agent", [src_a, src_b])  # repite src_a → dedupe

    prompt, ordered = _build_synthesis_prompt("Pregunta?", [out1, out2])

    assert ordered[0].id == "src-a"
    assert ordered[1].id == "src-b"
    assert "[1] A —" in prompt and "[2] B —" in prompt
    # El bullet de lore_agent debe citar [1,2] (las dos fuentes que aporta)
    assert "[1,2]" in prompt


def test_synthesizer_offline_returns_response_with_aggregated_confidence() -> None:
    """En modo offline el synthesizer devuelve texto determinístico y agrega confidence."""
    synth = Synthesizer(llm=LLMClient(api_key=""))  # offline forzado
    src = Source(id="s1", title="T", url="https://x.com", kind="dataset")
    outputs = [
        _resp("stats_agent", [src], conf=0.8),
        _resp("strategy_agent", [src], conf=0.6),
    ]
    ai = AgentInput(query="¿Qué tipos tiene Garchomp?")

    result = synth.run(ai, agent_outputs=outputs)

    assert result.agent == "synthesizer"
    assert result.content.startswith("[offline:light:")
    assert len(result.sources) == 1  # dedupe
    assert 0.6 <= result.confidence <= 0.85
    assert result.data["sub_agents"] == ["stats_agent", "strategy_agent"]


def test_synthesizer_handles_empty_outputs() -> None:
    synth = Synthesizer(llm=LLMClient(api_key=""))
    ai = AgentInput(query="?")
    result = synth.run(ai, agent_outputs=[])
    assert result.confidence == 0.1
    assert "No tengo información suficiente" in result.content


def test_synthesizer_calculator_anchors_confidence() -> None:
    """Si calculator_agent participa, el agregado debe estar cerca de 1.0."""
    synth = Synthesizer(llm=LLMClient(api_key=""))
    src = Source(id="formula", title="Gen IX", url=None, kind="computed")
    outputs = [
        _resp("calculator_agent", [src], conf=1.0),
        _resp("stats_agent", [src], conf=0.6),
    ]
    ai = AgentInput(query="Daño?")
    result = synth.run(ai, agent_outputs=outputs)
    assert result.confidence > 0.7


def test_synthesizer_stream_yields_tokens() -> None:
    synth = Synthesizer(llm=LLMClient(api_key=""))
    ai = AgentInput(query="?")
    src = Source(id="s", title="t", url=None, kind="dataset")
    chunks = list(synth.stream(ai, agent_outputs=[_resp("stats_agent", [src])]))
    full = "".join(chunks)
    assert full.startswith("[offline:light:")

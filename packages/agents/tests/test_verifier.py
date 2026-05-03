"""Tests del VerifierAgent: reglas individuales y batch."""

from __future__ import annotations

from agents.base import AgentResponse
from agents.verifier_agent import VerifierAgent
from shared.types import Source


def _resp(
    agent: str,
    *,
    content: str = "ok",
    confidence: float = 0.5,
    sources: list[Source] | None = None,
    data: dict | None = None,
) -> AgentResponse:
    return AgentResponse(
        agent=agent,
        content=content,
        confidence=confidence,
        sources=sources or [],
        data=data or {},
        trace_id="t-1",
    )


def test_calculator_response_passes_through_unchanged() -> None:
    v = VerifierAgent()
    r = _resp("calculator_agent", confidence=1.0, data={"damage": 120})
    out = v.verify(r)
    assert out.confidence == 1.0
    assert out is r  # la regla devuelve la misma instancia


def test_two_sources_boosts_confidence() -> None:
    v = VerifierAgent()
    src_a = Source(id="a", title="A", url=None, kind="dataset")
    src_b = Source(id="b", title="B", url=None, kind="bulbapedia")
    r = _resp("lore_agent", confidence=0.6, sources=[src_a, src_b])
    out = v.verify(r)
    assert out.confidence == 0.7  # +0.10


def test_numbers_without_data_degrades_confidence() -> None:
    v = VerifierAgent()
    r = _resp("stats_agent", confidence=0.9, content="Garchomp tiene 130 de Attack y 102 de Speed.")
    out = v.verify(r)
    assert out.confidence == 0.5


def test_verify_batch_runs_all_rules() -> None:
    v = VerifierAgent()
    src_a = Source(id="a", title="A", url=None, kind="dataset")
    src_b = Source(id="b", title="B", url=None, kind="dataset")
    responses = [
        _resp("lore_agent", confidence=0.6, sources=[src_a, src_b]),
        _resp("calculator_agent", confidence=1.0, data={"damage": 120}),
    ]
    out = v.verify_batch(responses)
    assert len(out) == 2
    # lore_agent recibió +0.10 por dos fuentes
    lore = next(r for r in out if r.agent == "lore_agent")
    assert lore.confidence >= 0.7


def test_verify_batch_empty_returns_empty() -> None:
    assert VerifierAgent().verify_batch([]) == []


def test_rag_agents_with_shared_names_get_boost() -> None:
    """Si lore + strategy mencionan los mismos Pokémon, suben confidence."""
    v = VerifierAgent()
    lore = _resp(
        "lore_agent",
        confidence=0.6,
        content="Pikachu y Charizard aparecen en Kanto frecuentemente.",
    )
    strategy = _resp(
        "strategy_agent",
        confidence=0.6,
        content="Pikachu y Charizard tienen rol ofensivo en OU.",
    )
    out = v.verify_batch([lore, strategy])
    assert all(r.confidence > 0.6 for r in out)

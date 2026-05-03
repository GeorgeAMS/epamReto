"""Smoke tests del paquete `agents`. Día 2 reemplaza por suite real."""

from __future__ import annotations

from agents.base import AgentInput, AgentResponse


def test_agent_input_defaults_have_trace_id() -> None:
    """``AgentInput`` genera trace_id automáticamente si no se provee."""
    a = AgentInput(query="hola")
    assert a.query == "hola"
    assert isinstance(a.trace_id, str)
    assert len(a.trace_id) >= 8


def test_agent_response_confidence_level_mapping() -> None:
    """Score 0.95 debe mapear a verified."""
    r = AgentResponse(
        agent="dummy",
        content="ok",
        confidence=0.95,
        trace_id="t-1",
    )
    assert r.confidence_level.value == "verified"

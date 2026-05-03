"""Tests de la memoria conversacional."""

from __future__ import annotations

from domain.conversation.entities import Conversation, Turn, TurnRole
from domain.conversation.services import ContextResolver


def test_resolver_recovers_recent_pokemon() -> None:
    convo = Conversation()
    convo.append(Turn(role=TurnRole.USER, content="¿Stats de Garchomp?"))
    convo.append(
        Turn(
            role=TurnRole.ASSISTANT,
            content="Garchomp 108/130/95...",
            mentioned_pokemon=("Garchomp",),
        )
    )
    convo.append(Turn(role=TurnRole.USER, content="¿y contra Gengar?"))

    ctx = ContextResolver().resolve(convo)
    assert "Garchomp" in ctx.active_pokemon


def test_resolver_handles_empty_history() -> None:
    ctx = ContextResolver().resolve(Conversation())
    assert ctx.active_pokemon == ()
    assert ctx.last_assistant_summary is None

"""Domain services del bounded context Conversation.

`ContextResolver` toma un `Conversation` y la pregunta actual y devuelve
un `ResolvedContext` con las entidades activas (Pokémon, moves) que el
orquestador necesita para resolver pronombres tipo "¿y contra Gengar?".

Nota: aquí solo aplicamos heurísticas determinísticas. El detalle fino
(NER por LLM) lo hace `agents/orchestrator.py` en otra capa.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.conversation.entities import Conversation


@dataclass(frozen=True)
class ResolvedContext:
    """Contexto resuelto a partir del historial.

    `active_pokemon`: Pokémon que el usuario probablemente sigue refiriéndose
    si la nueva pregunta usa pronombres ("ese", "él", "y contra X?").
    """

    active_pokemon: tuple[str, ...] = field(default_factory=tuple)
    active_moves: tuple[str, ...] = field(default_factory=tuple)
    last_assistant_summary: str | None = None


class ContextResolver:
    """Heurísticas simples de resolución de contexto.

    Estrategia Día 1:
    - Tomar los Pokémon/moves mencionados en los últimos N turnos.
    - Priorizar los del último turno del asistente (suelen ser sujeto activo).
    """

    def __init__(self, *, window_size: int = 4) -> None:
        self.window_size = window_size

    def resolve(self, conversation: Conversation) -> ResolvedContext:
        recent = conversation.last_n(self.window_size)
        if not recent:
            return ResolvedContext()

        seen_pokemon: list[str] = []
        seen_moves: list[str] = []
        last_assistant: str | None = None

        for turn in reversed(recent):
            for p in turn.mentioned_pokemon:
                if p not in seen_pokemon:
                    seen_pokemon.append(p)
            for m in turn.mentioned_moves:
                if m not in seen_moves:
                    seen_moves.append(m)
            if last_assistant is None and turn.role.value == "assistant":
                last_assistant = turn.content[:280]

        return ResolvedContext(
            active_pokemon=tuple(seen_pokemon[:5]),
            active_moves=tuple(seen_moves[:5]),
            last_assistant_summary=last_assistant,
        )


__all__ = ["ContextResolver", "ResolvedContext"]

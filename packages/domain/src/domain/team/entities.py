"""Entidades del bounded context Team Building.

Reglas básicas formato Singles:
- 6 miembros máximo (en Day 1 lo dejamos como invariante).
- Cada miembro porta un Pokémon configurado + 4 moves activos.
- Item y rol son metadata útil para el strategy_agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.pokemon.entities import Move, Pokemon
from shared.errors import ValidationError


@dataclass(frozen=True)
class TeamMember:
    """Pokémon + moves seleccionados + rol en el equipo."""

    pokemon: Pokemon
    moves: tuple[Move, ...]
    role: str = "flex"  # sweeper | wallbreaker | wall | pivot | hazard_setter | cleric | flex

    def __post_init__(self) -> None:
        if not 1 <= len(self.moves) <= 4:
            raise ValidationError(
                "Un miembro debe tener entre 1 y 4 movimientos",
                details={"pokemon": self.pokemon.name, "moves": len(self.moves)},
            )


@dataclass(frozen=True)
class Team:
    """Equipo competitivo (Singles)."""

    name: str
    members: tuple[TeamMember, ...] = field(default_factory=tuple)
    format: str = "singles"  # singles | doubles | vgc-2026

    def __post_init__(self) -> None:
        if not 1 <= len(self.members) <= 6:
            raise ValidationError(
                "Un equipo válido tiene entre 1 y 6 miembros",
                details={"team": self.name, "size": len(self.members)},
            )
        names = [m.pokemon.name.lower() for m in self.members]
        if len(set(names)) != len(names):
            raise ValidationError(
                "Species clause: no se permiten Pokémon repetidos",
                details={"team": self.name, "members": names},
            )


__all__ = ["Team", "TeamMember"]

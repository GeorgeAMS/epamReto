"""Entidades de la memoria conversacional.

Modelo simple: una `Conversation` agrega `Turn`s. Cada `Turn` puede portar
`Citation`s (las que se renderizan como `[1]`, `[2]` en la UI).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from shared.errors import ValidationError
from shared.types import ConfidenceLevel


class TurnRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True)
class Citation:
    """Cita estable consumida por la UI."""

    id: str
    title: str
    url: str | None = None
    snippet: str | None = None
    kind: str = "unknown"


@dataclass(frozen=True)
class Turn:
    """Un turno (mensaje) dentro de una conversación."""

    role: TurnRole
    content: str
    id: str = field(default_factory=lambda: uuid4().hex)
    citations: tuple[Citation, ...] = ()
    confidence: ConfidenceLevel = ConfidenceLevel.PARTIAL
    mentioned_pokemon: tuple[str, ...] = ()
    mentioned_moves: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.content.strip() and self.role != TurnRole.SYSTEM:
            raise ValidationError(
                "Un turno user/assistant no puede tener contenido vacío",
                details={"role": self.role.value},
            )


@dataclass
class Conversation:
    """Conversación mutable: vamos agregando turnos.

    No es ``frozen`` deliberadamente: la conversación es la única entidad
    que crece con el tiempo y vive ligada a una sesión del usuario.
    """

    id: str = field(default_factory=lambda: uuid4().hex)
    turns: list[Turn] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def append(self, turn: Turn) -> None:
        self.turns.append(turn)

    def last_n(self, n: int) -> list[Turn]:
        return self.turns[-n:] if n > 0 else []

    def latest_user_turn(self) -> Turn | None:
        for turn in reversed(self.turns):
            if turn.role == TurnRole.USER:
                return turn
        return None


__all__ = ["Citation", "Conversation", "Turn", "TurnRole"]

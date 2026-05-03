"""Store de conversaciones en memoria.

Para hackathon evitamos persistencia: cada proceso mantiene su propio dict.
Cuando lleguemos a Día 5 lo migramos a SQLite/Redis sin tocar la API pública
(sólo cambia la implementación de ``ConversationStore``).
"""

from __future__ import annotations

import threading
from collections.abc import Iterator

from agents.base import AgentResponse
from domain.conversation.entities import Citation, Conversation, Turn, TurnRole
from shared.errors import ValidationError
from shared.types import ConfidenceLevel, confidence_to_level


def _to_citations(response: AgentResponse) -> tuple[Citation, ...]:
    return tuple(
        Citation(
            id=src.id,
            title=src.title,
            url=src.url,
            snippet=src.snippet,
            kind=src.kind,
        )
        for src in response.sources
    )


class ConversationStore:
    """Store thread-safe de conversaciones."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._conversations: dict[str, Conversation] = {}

    def create(self, conversation_id: str | None = None) -> Conversation:
        with self._lock:
            conv = Conversation() if conversation_id is None else Conversation(id=conversation_id)
            self._conversations[conv.id] = conv
            return conv

    def get(self, conversation_id: str) -> Conversation | None:
        with self._lock:
            return self._conversations.get(conversation_id)

    def get_or_create(self, conversation_id: str | None) -> Conversation:
        if conversation_id:
            with self._lock:
                conv = self._conversations.get(conversation_id)
                if conv is not None:
                    return conv
        return self.create(conversation_id)

    def list(self) -> list[Conversation]:
        with self._lock:
            return list(self._conversations.values())

    def delete(self, conversation_id: str) -> bool:
        with self._lock:
            return self._conversations.pop(conversation_id, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._conversations.clear()

    # --- Helpers de turnos ----------------------------------------------

    def append_user_turn(self, conversation_id: str, query: str) -> Turn:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise ValidationError(
                "Conversación no encontrada",
                details={"conversation_id": conversation_id},
            )
        with self._lock:
            turn = Turn(role=TurnRole.USER, content=query)
            conv.append(turn)
            return turn

    def append_assistant_turn(
        self,
        conversation_id: str,
        response: AgentResponse,
    ) -> Turn:
        conv = self._conversations.get(conversation_id)
        if conv is None:
            raise ValidationError(
                "Conversación no encontrada",
                details={"conversation_id": conversation_id},
            )
        with self._lock:
            level: ConfidenceLevel = confidence_to_level(response.confidence)
            turn = Turn(
                role=TurnRole.ASSISTANT,
                content=response.content,
                citations=_to_citations(response),
                confidence=level,
            )
            conv.append(turn)
            return turn

    def find_response_by_trace(self, trace_id: str) -> AgentResponse | None:
        """Búsqueda lineal — basta para hackathon. Devuelve el último assistant
        turn cuya información corresponde al ``trace_id`` solicitado.

        Ojo: el ``Turn`` no almacena la ``AgentResponse`` completa (sólo los
        campos visibles). Los routers que necesiten re-ejecutar deben llamar
        de nuevo al orchestrator con la query original.
        """
        # Implementación reservada para Día 5 cuando agreguemos un mapa
        # ``trace_id → AgentResponse`` paralelo. Por ahora devolvemos None
        # y los reportes se generan re-ejecutando el orchestrator.
        return None

    # --- Iteración para tests --------------------------------------------

    def __iter__(self) -> Iterator[Conversation]:
        return iter(self.list())


__all__ = ["ConversationStore"]

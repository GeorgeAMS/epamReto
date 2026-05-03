"""Tests del LoreAgent y StrategyAgent — graceful fallback sin Qdrant.

Para no depender de Qdrant levantado, inyectamos un VectorStore fake que
simula tanto "colección vacía" como "colección con hits".
"""

from __future__ import annotations

from typing import Any

from agents.base import AgentInput
from agents.lore_agent import LoreAgent
from agents.strategy_agent import StrategyAgent
from infrastructure.llm_client import LLMClient
from infrastructure.vector_store import SearchHit


class _FakeStore:
    """Store mínimo que devuelve hits o lanza para simular Qdrant offline."""

    def __init__(
        self,
        hits: list[SearchHit] | None = None,
        *,
        raise_on_search: bool = False,
    ) -> None:
        self._hits = hits or []
        self._raise = raise_on_search

    def search_text(self, **_: Any) -> list[SearchHit]:
        if self._raise:
            raise ConnectionError("Qdrant no disponible")
        return list(self._hits)


def test_lore_agent_no_collection_returns_zero_confidence() -> None:
    agent = LoreAgent(
        llm=LLMClient(api_key=""),
        store=_FakeStore(raise_on_search=True),  # type: ignore[arg-type]
    )
    response = agent.run(AgentInput(query="lore de Mewtwo"))
    assert response.confidence == 0.0
    assert "no disponible" in response.content.lower() or "no encontré" in response.content.lower()


def test_lore_agent_empty_hits_returns_zero_confidence() -> None:
    agent = LoreAgent(
        llm=LLMClient(api_key=""),
        store=_FakeStore(hits=[]),  # type: ignore[arg-type]
    )
    response = agent.run(AgentInput(query="lore de Mewtwo"))
    assert response.confidence == 0.0


def test_lore_agent_with_hits_returns_sources_and_calls_llm() -> None:
    hits = [
        SearchHit(
            id="lore-1",
            score=0.9,
            payload={
                "title": "Mewtwo (anime)",
                "url": "https://bulbapedia.bulbagarden.net/wiki/Mewtwo",
                "text": "Mewtwo apareció por primera vez en la película de 1998.",
            },
        ),
        SearchHit(
            id="lore-2",
            score=0.8,
            payload={"title": "Manga", "url": None, "text": "En el manga de Origins..."},
        ),
    ]
    agent = LoreAgent(
        llm=LLMClient(api_key=""),
        store=_FakeStore(hits=hits),  # type: ignore[arg-type]
    )
    response = agent.run(AgentInput(query="lore de Mewtwo"))
    assert len(response.sources) == 2
    assert response.confidence >= 0.6
    assert response.sources[0].kind == "bulbapedia"


def test_strategy_agent_without_corpus_or_team_returns_zero_confidence() -> None:
    agent = StrategyAgent(
        llm=LLMClient(api_key=""),
        store=_FakeStore(raise_on_search=True),  # type: ignore[arg-type]
    )
    response = agent.run(AgentInput(query="cobertura para Dragapult"))
    assert response.confidence == 0.0


def test_strategy_agent_with_smogon_hits_returns_sources() -> None:
    hits = [
        SearchHit(
            id="strat-1",
            score=0.9,
            payload={
                "title": "Dragapult OU analysis",
                "url": "https://www.smogon.com/dex/sv/pokemon/dragapult/",
                "text": "Dragapult sweeper, win con foco en velocidad.",
            },
        ),
    ]
    agent = StrategyAgent(
        llm=LLMClient(api_key=""),
        store=_FakeStore(hits=hits),  # type: ignore[arg-type]
    )
    response = agent.run(AgentInput(query="¿Cómo cubro debilidades de Dragapult?"))
    assert response.sources
    assert response.sources[0].kind == "smogon"

"""Tests del Orchestrator (LangGraph) en modo offline.

Inyectamos sub-agentes fake para no depender de PokéAPI/Qdrant: el objetivo
es validar la **topología del grafo** (classify → dispatch → verify → synthesize),
no la implementación de cada sub-agente (que tiene sus propios tests).
"""

from __future__ import annotations

import json

from agents.base import AgentInput, AgentResponse, BaseAgent
from agents.orchestrator import Intent, Orchestrator, _heuristic_intent
from infrastructure.llm_client import LLMClient
from shared.types import Source


class _FakeAgent(BaseAgent):
    def __init__(self, name: str, *, confidence: float = 0.7) -> None:
        super().__init__(name=name)
        self._conf = confidence

    def execute(self, state: dict) -> dict:
        """Ruta rápida del grafo: emula stats JSON sin red."""
        ent = state.get("entities") or {}
        name = ent.get("pokemon", "pikachu")
        if isinstance(name, list):
            name = name[0] if name else "pikachu"
        slug = str(name).lower().replace(" ", "-")
        state["stats_response"] = json.dumps(
            {
                "name": slug,
                "types": ["normal"],
                "base_stats": {
                    "hp": 50,
                    "attack": 50,
                    "defense": 50,
                    "special_attack": 50,
                    "special_defense": 50,
                    "speed": 50,
                    "total": 300,
                },
                "ability": "pressure",
            },
            ensure_ascii=False,
        )
        return state

    def run(self, agent_input: AgentInput) -> AgentResponse:
        return AgentResponse(
            agent=self.name,
            content=f"Fake output del {self.name} para query: {agent_input.query}",
            sources=[
                Source(
                    id=f"{self.name}:fake-1",
                    title=f"Fuente {self.name}",
                    url=f"https://example.com/{self.name}",
                    kind="dataset",
                )
            ],
            confidence=self._conf,
            trace_id=agent_input.trace_id,
        )


def _build_orch() -> Orchestrator:
    """Helper: orchestrator con LLM offline + agentes fake."""
    llm = LLMClient(api_key="")  # offline forzado
    return Orchestrator(
        llm=llm,
        stats_agent=_FakeAgent("stats_agent", confidence=0.9),  # type: ignore[arg-type]
        calculator_agent=_FakeAgent("calculator_agent", confidence=1.0),  # type: ignore[arg-type]
        lore_agent=_FakeAgent("lore_agent", confidence=0.6),  # type: ignore[arg-type]
        strategy_agent=_FakeAgent("strategy_agent", confidence=0.7),  # type: ignore[arg-type]
    )


def test_heuristic_intent_classification() -> None:
    assert _heuristic_intent("¿Qué stats tiene Garchomp?") == Intent.STATS
    assert _heuristic_intent("calcula daño de Blizzard") == Intent.CALC
    assert _heuristic_intent("Build me a competitive OU team") == Intent.STRATEGY
    assert _heuristic_intent("Cuéntame el lore de Mewtwo en el anime") == Intent.LORE
    assert _heuristic_intent("Hola Pokédex") == Intent.MIXED


def test_orchestrator_handle_stats_intent_runs_full_graph() -> None:
    """Stats query → classify → stats (JSON) → synthesize rápido."""
    orch = _build_orch()
    response = orch.handle("¿Qué stats tiene Garchomp?", trace_id="trace-stats")  # type: ignore[arg-type]
    assert response.agent == "synthesizer"
    assert response.trace_id == "trace-stats"
    assert "garchomp" in response.content.lower()
    assert any(s.id.startswith("pokeapi:") for s in response.sources)


def test_orchestrator_handle_strategy_intent_invokes_two_agents() -> None:
    """Grafo rápido: aunque la intención sea strategy, solo corre stats + synth."""
    orch = _build_orch()
    response = orch.handle(
        "estrategia smogon para Garchomp en OU",
        trace_id="trace-strat",
    )  # type: ignore[arg-type]
    assert response.agent == "synthesizer"
    assert "garchomp" in response.content.lower()
    assert any(s.id.startswith("pokeapi:") for s in response.sources)


def test_orchestrator_handle_mixed_runs_three_agents() -> None:
    orch = _build_orch()
    response = orch.handle("Hola, cuéntame de Pikachu", trace_id="trace-mixed")  # type: ignore[arg-type]
    assert response.agent == "synthesizer"
    assert "pikachu" in response.content.lower()
    assert any(s.id.startswith("pokeapi:") for s in response.sources)


def test_orchestrator_handle_calc_without_payload_skips_calculator() -> None:
    """Ruta rápida: calc intent sigue resolviendo stats del Pokémon detectado."""
    orch = _build_orch()
    response = orch.handle("calcula daño de Blizzard con Pikachu", trace_id="trace-calc")  # type: ignore[arg-type]
    assert response.agent == "synthesizer"
    assert "pikachu" in response.content.lower()


def test_orchestrator_handle_stream_emits_intent_agent_token_done() -> None:
    """El generador stream emite los 4 tipos de eventos en orden."""
    orch = _build_orch()
    events = list(orch.handle_stream("¿Qué stats tiene Garchomp?", trace_id="trace-stream"))  # type: ignore[arg-type]
    event_types = [e["event"] for e in events]
    assert event_types[0] == "intent"
    assert "agent" in event_types
    assert "token" in event_types
    assert event_types[-1] == "done"

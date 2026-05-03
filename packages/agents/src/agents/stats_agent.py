"""Stats agent — consultas factuales sobre PokéAPI / DuckDB.

Día 1: stub mínimo que delega a ``PokeAPIClient.to_domain_pokemon``. Día 2
añadiremos NER del query, soporte DuckDB y formato tabular en la respuesta.
"""

from __future__ import annotations

import json

from agents.base import AgentInput, AgentResponse, BaseAgent
from infrastructure.observability import traced
from infrastructure.pokeapi_client import PokeAPIClient, get_client
from shared.errors import InfrastructureError
from shared.logging import get_logger
from shared.types import Source

logger = get_logger(__name__)


class StatsAgent(BaseAgent):
    name = "stats_agent"

    def __init__(self, *, client: PokeAPIClient | None = None) -> None:
        super().__init__(name=self.name)
        self._client_override = client

    @property
    def _client(self) -> PokeAPIClient:
        # Lazy: solo inicializa la singleton cuando se ejecuta el agente.
        return self._client_override or get_client()

    @traced("stats_agent")
    def run(self, agent_input: AgentInput) -> AgentResponse:
        target_name = agent_input.context.get("pokemon_name") or agent_input.query
        try:
            pokemon = self._client.to_domain_pokemon(str(target_name))
        except InfrastructureError as e:
            return AgentResponse(
                agent=self.name,
                content=f"No pude encontrar datos para **{target_name}** ({e.message}).",
                confidence=0.2,
                trace_id=agent_input.trace_id,
            )

        bs = pokemon.base_stats
        types_str = "/".join(t.value.title() for t in pokemon.types)
        content = (
            f"**{pokemon.name}** ({types_str}). "
            f"Stats base: HP {bs.hp} · Atk {bs.attack} · Def {bs.defense} · "
            f"SpA {bs.special_attack} · SpD {bs.special_defense} · Spe {bs.speed} "
            f"(BST {bs.total}). Habilidad: *{pokemon.ability.name}*."
        )

        return AgentResponse(
            agent=self.name,
            content=content,
            confidence=0.95,
            sources=[
                Source(
                    id=f"pokeapi:{pokemon.name.lower()}",
                    title=f"PokéAPI · {pokemon.name}",
                    url=f"https://pokeapi.co/api/v2/pokemon/{pokemon.name.lower()}",
                    kind="pokeapi",
                )
            ],
            data={
                "name": pokemon.name,
                "types": [t.value for t in pokemon.types],
                "base_stats": {
                    "hp": bs.hp,
                    "attack": bs.attack,
                    "defense": bs.defense,
                    "special_attack": bs.special_attack,
                    "special_defense": bs.special_defense,
                    "speed": bs.speed,
                    "total": bs.total,
                },
                "ability": pokemon.ability.name,
            },
            trace_id=agent_input.trace_id,
        )

    def execute(self, state: dict) -> dict:
        """Optimización: JSON directo, sin formateo LLM."""
        entities = state.get("entities", {}) or {}
        pokemon_name = entities.get("pokemon", "pikachu")
        if isinstance(pokemon_name, list):
            pokemon_name = pokemon_name[0] if pokemon_name else "pikachu"
        try:
            data = self._client.get_pokemon_raw(str(pokemon_name))
            stat_map = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
            response = {
                "name": data["name"],
                "types": [t["type"]["name"] for t in sorted(data["types"], key=lambda x: x["slot"])],
                "base_stats": {
                    "hp": stat_map.get("hp", 0),
                    "attack": stat_map.get("attack", 0),
                    "defense": stat_map.get("defense", 0),
                    "special_attack": stat_map.get("special-attack", 0),
                    "special_defense": stat_map.get("special-defense", 0),
                    "speed": stat_map.get("speed", 0),
                    "total": sum(
                        stat_map.get(k, 0)
                        for k in (
                            "hp",
                            "attack",
                            "defense",
                            "special-attack",
                            "special-defense",
                            "speed",
                        )
                    ),
                },
                "ability": data["abilities"][0]["ability"]["name"] if data["abilities"] else "unknown",
            }
            state["stats_response"] = json.dumps(response, ensure_ascii=False)
            return state
        except Exception as e:
            logger.error(f"Stats agent error: {e}")
            state["stats_response"] = json.dumps({"error": str(e)})
            return state


__all__ = ["StatsAgent"]

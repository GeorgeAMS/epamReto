"""Calculator agent — función pura sobre el ``DamageCalculator``.

REGLA DE ORO: este agente NO invoca LLM. Recibe input estructurado y
delega a `domain.pokemon.services.DamageCalculator`. Esto garantiza
correctness numérico (criterio explícito de evaluación).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agents.base import AgentInput, AgentResponse, BaseAgent
from domain.pokemon.entities import Move, Pokemon
from domain.pokemon.services import DamageCalculator
from domain.pokemon.value_objects import BattleConditions
from infrastructure.observability import traced
from shared.types import Source


class CalculatorRequest(BaseModel):
    """Input estructurado que el orquestador empaqueta en ``AgentInput.context``."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    attacker: Pokemon
    defender: Pokemon
    move: Move
    conditions: BattleConditions = Field(default_factory=BattleConditions)


class CalculatorAgent(BaseAgent):
    """Calcula daño con la fórmula Gen IX y devuelve ``AgentResponse``."""

    name = "calculator_agent"

    @traced("calculator_agent")
    def run(self, agent_input: AgentInput) -> AgentResponse:
        request = self._extract_request(agent_input)
        result = DamageCalculator.calculate(
            attacker=request.attacker,
            defender=request.defender,
            move=request.move,
            conditions=request.conditions,
        )
        low, high = DamageCalculator.damage_range(
            attacker=request.attacker,
            defender=request.defender,
            move=request.move,
            conditions=request.conditions,
        )
        defender_hp = request.defender.effective_stats().hp
        attacker_stats = request.attacker.effective_stats()
        defender_stats = request.defender.effective_stats()
        pct_low = round(100 * low / defender_hp, 1) if defender_hp else 0.0
        pct_high = round(100 * high / defender_hp, 1) if defender_hp else 0.0

        move_power = request.move.power or 0
        move_type = request.move.type.value.title()
        move_cat = request.move.category.value.title()
        type_note = (
            f"Type effectiveness: {result.type_effectiveness}x "
            f"({move_type} vs {'/'.join(t.value.title() for t in request.defender.types)})."
        )
        notes_str = " ".join(result.notes) if result.notes else "Gen IX deterministic calculation."
        content = (
            f"{request.move.name} ({move_power} BP, {move_type}, {move_cat}) from "
            f"{request.attacker.name} (SpA {attacker_stats.special_attack}, nature {request.attacker.nature.name.title()}) "
            f"vs {request.defender.name} (SpD {defender_stats.special_defense}).\n\n"
            f"Damage: {low}-{high} HP ({pct_low}-{pct_high}% of total HP).\n"
            f"{type_note}\n"
            "Calculated with Gen IX damage formula.\n"
            f"Source: PokeAPI stats + DamageCalculator verified. {notes_str}"
        )

        data: dict[str, Any] = {
            "attacker_name": request.attacker.name,
            "defender_name": request.defender.name,
            "move_name": request.move.name,
            "damage": result.damage,
            "damage_range": [low, high],
            "percent_range": [pct_low, pct_high],
            "type_effectiveness": result.type_effectiveness,
            "stab": result.stab_multiplier,
            "crit": result.crit_multiplier,
            "weather": result.weather_multiplier,
            "terrain": result.terrain_multiplier,
            "burn": result.burn_multiplier,
            "screens": result.screens_multiplier,
            "is_immune": result.is_immune,
            "notes": list(result.notes),
        }

        return AgentResponse(
            agent=self.name,
            content=content,
            confidence=1.0,  # cálculo determinista
            sources=[
                Source(
                    id="formula:gen-ix-damage",
                    title="Fórmula de daño Gen IX (Bulbapedia)",
                    url="https://bulbapedia.bulbagarden.net/wiki/Damage",
                    kind="computed",
                )
            ],
            data=data,
            trace_id=agent_input.trace_id,
        )

    @staticmethod
    def _extract_request(agent_input: AgentInput) -> CalculatorRequest:
        ctx = agent_input.context
        if "calculator_request" in ctx and isinstance(ctx["calculator_request"], CalculatorRequest):
            return ctx["calculator_request"]
        return CalculatorRequest(**ctx)


__all__ = ["CalculatorAgent", "CalculatorRequest"]

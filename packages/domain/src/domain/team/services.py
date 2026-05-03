"""Domain services del bounded context Team.

`CoverageAnalyzer` produce la matriz "qué tipos puede golpear el equipo"
y "qué tipos amenazan al equipo" — la base de la heatmap del Team Builder
en la UI.

`SynergyScorer` da un score 0–1 (placeholder Día 1; se afina en Día 4).
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.pokemon.services import TypeEffectiveness
from domain.pokemon.value_objects import Type
from domain.team.entities import Team


@dataclass(frozen=True)
class CoverageReport:
    """Cobertura ofensiva y vulnerabilidades defensivas del equipo.

    Cada dict mapea ``Type → cantidad de miembros que cubren / son débiles``.
    """

    offensive: dict[Type, int]
    defensive_weaknesses: dict[Type, int]
    uncovered_types: list[Type]
    quad_weak_types: list[Type]


class CoverageAnalyzer:
    """Calcula cobertura cruzando los tipos atacantes (movimientos) y los
    tipos defensores (todos los 18 tipos posibles del meta)."""

    @staticmethod
    def analyze(team: Team) -> CoverageReport:
        offensive: dict[Type, int] = {t: 0 for t in Type}
        defensive_weaknesses: dict[Type, int] = {t: 0 for t in Type}

        for member in team.members:
            attacking_types = {m.type for m in member.moves}

            for defender_type in Type:
                if any(
                    TypeEffectiveness.single(atk, defender_type) >= 2.0
                    for atk in attacking_types
                ):
                    offensive[defender_type] += 1

            for atk_type in Type:
                effectiveness = 1.0
                for member_type in member.pokemon.types:
                    effectiveness *= TypeEffectiveness.single(atk_type, member_type)
                if effectiveness >= 2.0:
                    defensive_weaknesses[atk_type] += 1

        uncovered = [t for t, n in offensive.items() if n == 0]
        quad_weak: list[Type] = []
        for atk_type in Type:
            for member in team.members:
                eff = 1.0
                for member_type in member.pokemon.types:
                    eff *= TypeEffectiveness.single(atk_type, member_type)
                if eff >= 4.0:
                    quad_weak.append(atk_type)
                    break

        return CoverageReport(
            offensive=offensive,
            defensive_weaknesses=defensive_weaknesses,
            uncovered_types=uncovered,
            quad_weak_types=quad_weak,
        )


class SynergyScorer:
    """Score heurístico de sinergia 0–1 (placeholder Día 1).

    Día 4 lo refinamos con datos competitivos reales: roles cubiertos,
    pivot moves, hazard setters, win conditions, etc.
    """

    @staticmethod
    def score(team: Team) -> float:
        report = CoverageAnalyzer.analyze(team)
        offensive_breadth = sum(1 for n in report.offensive.values() if n > 0) / 18.0
        weakness_pressure = (
            sum(report.defensive_weaknesses.values()) / (18.0 * len(team.members))
        )
        quad_penalty = 0.1 * len(report.quad_weak_types)
        raw = offensive_breadth - 0.5 * weakness_pressure - quad_penalty
        return max(0.0, min(1.0, raw))


__all__ = ["CoverageAnalyzer", "CoverageReport", "SynergyScorer"]

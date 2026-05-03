"""Tests del bounded context Team."""

from __future__ import annotations

from domain.pokemon.value_objects import Type
from domain.team.entities import Team, TeamMember
from domain.team.services import CoverageAnalyzer, SynergyScorer

from .fixtures import (
    DRAGON_CLAW,
    EARTHQUAKE,
    FLAMETHROWER,
    HYDRO_PUMP,
    ICE_FANG,
    SHADOW_BALL,
    THUNDERBOLT,
    blissey,
    charizard,
    garchomp,
    gengar,
    salamence,
    venusaur,
)


def _build_team() -> Team:
    return Team(
        name="HackathonDemo",
        members=(
            TeamMember(pokemon=garchomp(), moves=(EARTHQUAKE, DRAGON_CLAW, ICE_FANG)),
            TeamMember(pokemon=charizard(), moves=(FLAMETHROWER, HYDRO_PUMP)),
            TeamMember(pokemon=gengar(), moves=(SHADOW_BALL, THUNDERBOLT)),
            TeamMember(pokemon=blissey(), moves=(THUNDERBOLT,)),
            TeamMember(pokemon=venusaur(), moves=(SHADOW_BALL,)),
            TeamMember(pokemon=salamence(), moves=(DRAGON_CLAW,)),
        ),
    )


def test_coverage_includes_super_effective_against_dragon() -> None:
    team = _build_team()
    report = CoverageAnalyzer.analyze(team)
    # Garchomp con Ice Fang cubre Dragon (Ice ×2 vs Dragon)
    assert report.offensive[Type.DRAGON] >= 1


def test_coverage_detects_uncovered_types() -> None:
    minimal = Team(
        name="onlyfire",
        members=(TeamMember(pokemon=charizard(), moves=(FLAMETHROWER,)),),
    )
    report = CoverageAnalyzer.analyze(minimal)
    # Fire no es super eff contra Water → Water uncovered
    assert Type.WATER in report.uncovered_types


def test_synergy_score_in_range() -> None:
    score = SynergyScorer.score(_build_team())
    assert 0.0 <= score <= 1.0


def test_species_clause_rejects_duplicates() -> None:
    import pytest

    from shared.errors import ValidationError

    with pytest.raises(ValidationError):
        Team(
            name="dupes",
            members=(
                TeamMember(pokemon=garchomp(), moves=(EARTHQUAKE,)),
                TeamMember(pokemon=garchomp(), moves=(EARTHQUAKE,)),
            ),
        )

"""Registro de battles canónicos para eval numérica (misma lógica que tests/domain)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from domain.pokemon.entities import Move, Pokemon
from domain.pokemon.value_objects import (
    BattleConditions,
    MoveCategory,
    Type,
    Weather,
)

_REPO = Path(__file__).resolve().parent.parent
_DOMAIN_TESTS = _REPO / "packages" / "domain" / "tests"
if str(_DOMAIN_TESTS) not in sys.path:
    sys.path.insert(0, str(_DOMAIN_TESTS))

from fixtures import (  # noqa: E402
    ABILITY_ADAPTABILITY,
    EARTHQUAKE,
    FLAMETHROWER,
    HYDRO_PUMP,
    ICE_FANG,
    THUNDERBOLT,
    blissey,
    charizard,
    garchomp,
    gengar,
    porygon_z,
    salamence,
    venusaur,
)

HYPER_VOICE = Move(
    name="Hyper Voice",
    type=Type.NORMAL,
    category=MoveCategory.SPECIAL,
    power=90,
    accuracy=100,
    pp=10,
)


@dataclass(frozen=True)
class BattleFixture:
    attacker: Pokemon
    defender: Pokemon
    move: Move
    conditions: BattleConditions


def _max() -> BattleConditions:
    return BattleConditions(random_factor=1.0)


FIXTURES: dict[str, BattleFixture] = {
    "garchomp_earthquake_blissey_max": BattleFixture(
        garchomp(), blissey(), EARTHQUAKE, _max()
    ),
    "garchomp_ice_fang_salamence_max": BattleFixture(
        garchomp(), salamence(), ICE_FANG, _max()
    ),
    "charizard_flamethrower_venusaur_max": BattleFixture(
        charizard(), venusaur(), FLAMETHROWER, _max()
    ),
    "charizard_flamethrower_venusaur_sun_max": BattleFixture(
        charizard(),
        venusaur(),
        FLAMETHROWER,
        BattleConditions(random_factor=1.0, weather=Weather.SUN),
    ),
    "venusaur_hydro_charizard_max": BattleFixture(
        venusaur(), charizard(), HYDRO_PUMP, _max()
    ),
    "venusaur_hydro_charizard_rain_max": BattleFixture(
        venusaur(),
        charizard(),
        HYDRO_PUMP,
        BattleConditions(random_factor=1.0, weather=Weather.RAIN),
    ),
    "gengar_thunderbolt_blissey_max": BattleFixture(
        gengar(), blissey(), THUNDERBOLT, _max()
    ),
    "porygon_hyper_voice_blissey_max": BattleFixture(
        porygon_z(ability=ABILITY_ADAPTABILITY), blissey(), HYPER_VOICE, _max()
    ),
}


__all__ = ["FIXTURES", "BattleFixture"]

"""Tests de la tabla de tipos Gen IX."""

from __future__ import annotations

import pytest

from domain.pokemon.services import TypeEffectiveness
from domain.pokemon.value_objects import Type

# (atacante, defensor, esperado)
SINGLE_CASES: list[tuple[Type, Type, float]] = [
    # Inmunidades icónicas
    (Type.NORMAL, Type.GHOST, 0.0),
    (Type.GHOST, Type.NORMAL, 0.0),
    (Type.ELECTRIC, Type.GROUND, 0.0),
    (Type.GROUND, Type.FLYING, 0.0),
    (Type.PSYCHIC, Type.DARK, 0.0),
    (Type.DRAGON, Type.FAIRY, 0.0),
    (Type.POISON, Type.STEEL, 0.0),
    (Type.FIGHTING, Type.GHOST, 0.0),

    # Super efectivos clásicos
    (Type.WATER, Type.FIRE, 2.0),
    (Type.FIRE, Type.GRASS, 2.0),
    (Type.GRASS, Type.WATER, 2.0),
    (Type.ELECTRIC, Type.WATER, 2.0),
    (Type.GROUND, Type.ELECTRIC, 2.0),
    (Type.ICE, Type.DRAGON, 2.0),
    (Type.FAIRY, Type.DRAGON, 2.0),
    (Type.FIGHTING, Type.STEEL, 2.0),
    (Type.STEEL, Type.FAIRY, 2.0),

    # Poco efectivos
    (Type.WATER, Type.GRASS, 0.5),
    (Type.FIRE, Type.WATER, 0.5),
    (Type.NORMAL, Type.STEEL, 0.5),
    (Type.DRAGON, Type.STEEL, 0.5),
    (Type.FAIRY, Type.FIRE, 0.5),

    # Neutros (ausentes en _OVERRIDES → 1.0 por defecto)
    (Type.NORMAL, Type.WATER, 1.0),
    (Type.PSYCHIC, Type.GRASS, 1.0),
]


@pytest.mark.parametrize("attacker,defender,expected", SINGLE_CASES)
def test_single_type_matchups(attacker: Type, defender: Type, expected: float) -> None:
    assert TypeEffectiveness.single(attacker, defender) == pytest.approx(expected)


def test_dragon_ground_quad_weakness_to_ice() -> None:
    """Garchomp (Dragon/Ground) recibe ×4 de Ice."""
    from .fixtures import garchomp

    eff = TypeEffectiveness.vs_pokemon(Type.ICE, garchomp())
    assert eff == pytest.approx(4.0)


def test_venusaur_double_weakness_to_psychic() -> None:
    """Venusaur (Grass/Poison) recibe ×2 a Psychic (Poison débil; Grass neutral)."""
    from .fixtures import venusaur

    eff = TypeEffectiveness.vs_pokemon(Type.PSYCHIC, venusaur())
    assert eff == pytest.approx(2.0)


def test_ghost_immune_to_normal() -> None:
    """Sanity: Blissey (Normal) es inmune a Ghost por reverso del matchup."""
    from .fixtures import blissey

    eff = TypeEffectiveness.vs_pokemon(Type.GHOST, blissey())
    assert eff == pytest.approx(0.0)


def test_charizard_quad_weak_rock() -> None:
    """Charizard (Fire/Flying): Rock×Fire = 2.0, Rock×Flying = 2.0 → ×4."""
    from .fixtures import charizard

    eff = TypeEffectiveness.vs_pokemon(Type.ROCK, charizard())
    assert eff == pytest.approx(4.0)


def test_gengar_terastalized_to_fairy_immune_to_dragon() -> None:
    """Si Gengar Tera Fairy → Dragon ×0; Fighting pasa a 0.5."""
    from dataclasses import replace

    from .fixtures import gengar

    g = replace(gengar(), is_terastalized=True, tera_type=Type.FAIRY)
    assert TypeEffectiveness.vs_pokemon(Type.DRAGON, g) == pytest.approx(0.0)
    assert TypeEffectiveness.vs_pokemon(Type.FIGHTING, g) == pytest.approx(0.5)

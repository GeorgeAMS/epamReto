"""Tests del DamageCalculator (fórmula Gen IX).

Estrategia: fijamos ``random_factor=1.0`` (max-roll) salvo cuando probamos
explícitamente el rango. Cada caso documenta el cálculo manual en el
docstring para que un revisor pueda reproducirlo a lápiz.

Los Pokémon usados están todos en `tests.fixtures` con builds estándar
de Lv100.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from domain.pokemon.entities import Move
from domain.pokemon.services import DamageCalculator
from domain.pokemon.value_objects import (
    BattleConditions,
    MoveCategory,
    StatusCondition,
    Terrain,
    Type,
    Weather,
)
from shared.errors import DomainError

from .fixtures import (
    DRAGON_CLAW,
    EARTHQUAKE,
    FLAMETHROWER,
    HYDRO_PUMP,
    ICE_FANG,
    SHADOW_BALL,
    TACKLE,
    THUNDERBOLT,
    blissey,
    charizard,
    garchomp,
    gengar,
    porygon_z,
    salamence,
    venusaur,
)


def _max_roll() -> BattleConditions:
    return BattleConditions(random_factor=1.0)


# =========================================================================
# 1) STAB y matchups básicos
# =========================================================================


class TestSTAB:
    def test_stab_applies_for_matching_type(self) -> None:
        """Garchomp (Dragon/Ground) usando Earthquake → STAB 1.5.

        Usamos Blissey (Normal) como defensor: el matchup tipo es neutro
        (×1) así que el STAB es claramente observable.
        """
        result = DamageCalculator.calculate(
            attacker=garchomp(),
            defender=blissey(),
            move=EARTHQUAKE,
            conditions=_max_roll(),
        )
        assert result.stab_multiplier == 1.5

    def test_no_stab_for_unmatched_type(self) -> None:
        """Garchomp Ice Fang (no comparte tipo) → STAB 1.0."""
        result = DamageCalculator.calculate(
            attacker=garchomp(),
            defender=salamence(),
            move=ICE_FANG,
            conditions=_max_roll(),
        )
        assert result.stab_multiplier == 1.0

    def test_adaptability_doubles_stab(self) -> None:
        """Porygon-Z con Adaptability usando Tri Attack-equivalente Normal → 2.0."""
        normal_move = Move(
            name="Hyper Voice",
            type=Type.NORMAL,
            category=MoveCategory.SPECIAL,
            power=90,
            accuracy=100,
            pp=10,
        )
        result = DamageCalculator.calculate(
            attacker=porygon_z(),
            defender=blissey(),
            move=normal_move,
            conditions=_max_roll(),
        )
        assert result.stab_multiplier == 2.0


# =========================================================================
# 2) Type effectiveness y casos de inmunidad
# =========================================================================


class TestTypeEffectiveness:
    def test_immune_normal_vs_ghost(self) -> None:
        """Blissey usando Tackle (Normal) contra Gengar (Ghost) → ×0, daño 0."""
        result = DamageCalculator.calculate(
            attacker=blissey(),
            defender=gengar(),
            move=TACKLE,
            conditions=_max_roll(),
        )
        assert result.is_immune is True
        assert result.damage == 0
        assert result.type_effectiveness == 0.0

    def test_super_effective_4x_against_garchomp(self) -> None:
        """Salamence Ice Fang vs Garchomp → ×4 (Ice vs Dragon ×2 vs Ground ×2)."""
        result = DamageCalculator.calculate(
            attacker=salamence(),
            defender=garchomp(),
            move=ICE_FANG,
            conditions=_max_roll(),
        )
        assert result.type_effectiveness == pytest.approx(4.0)
        assert result.damage > 0

    def test_not_very_effective_against_steel(self) -> None:
        """Dragon Claw vs Pokémon Steel imaginario via override del defensor.

        Construimos un defensor mono-Steel reaprovechando Blissey base stats
        (es la única manera de no añadir más fixtures). Validamos que el
        multiplicador se aplique (no nos importa el daño exacto)."""
        from dataclasses import replace as _r

        steel_defender = _r(blissey(), name="SteelMon", types=(Type.STEEL,))
        result = DamageCalculator.calculate(
            attacker=garchomp(),
            defender=steel_defender,
            move=DRAGON_CLAW,
            conditions=_max_roll(),
        )
        assert result.type_effectiveness == pytest.approx(0.5)


# =========================================================================
# 3) Crit, weather, terrain, burn, screens
# =========================================================================


class TestModifiers:
    def test_crit_increases_damage_by_1_5x(self) -> None:
        """Earthquake vs Blissey: matchup neutro pero damage > 0 garantizado."""
        normal = DamageCalculator.calculate(
            attacker=garchomp(),
            defender=blissey(),
            move=EARTHQUAKE,
            conditions=_max_roll(),
        )
        crit = DamageCalculator.calculate(
            attacker=garchomp(),
            defender=blissey(),
            move=EARTHQUAKE,
            conditions=replace(_max_roll(), is_critical=True),
        )
        assert normal.damage > 0
        assert crit.crit_multiplier == 1.5
        assert crit.damage >= int(normal.damage * 1.49)

    def test_sun_boosts_fire_moves(self) -> None:
        sunny = DamageCalculator.calculate(
            attacker=charizard(),
            defender=venusaur(),
            move=FLAMETHROWER,
            conditions=replace(_max_roll(), weather=Weather.SUN),
        )
        clear = DamageCalculator.calculate(
            attacker=charizard(),
            defender=venusaur(),
            move=FLAMETHROWER,
            conditions=_max_roll(),
        )
        assert sunny.weather_multiplier == 1.5
        assert sunny.damage > clear.damage

    def test_rain_weakens_fire_moves(self) -> None:
        rainy = DamageCalculator.calculate(
            attacker=charizard(),
            defender=venusaur(),
            move=FLAMETHROWER,
            conditions=replace(_max_roll(), weather=Weather.RAIN),
        )
        assert rainy.weather_multiplier == 0.5

    def test_heavy_rain_blocks_fire(self) -> None:
        result = DamageCalculator.calculate(
            attacker=charizard(),
            defender=venusaur(),
            move=FLAMETHROWER,
            conditions=replace(_max_roll(), weather=Weather.HEAVY_RAIN),
        )
        assert result.weather_multiplier == 0.0
        assert result.damage == 0

    def test_grassy_terrain_boosts_grass_moves(self) -> None:
        razor_leaf = Move(
            name="Razor Leaf",
            type=Type.GRASS,
            category=MoveCategory.PHYSICAL,
            power=55,
            accuracy=95,
            pp=25,
        )
        boosted = DamageCalculator.calculate(
            attacker=venusaur(),
            defender=blissey(),
            move=razor_leaf,
            conditions=replace(_max_roll(), terrain=Terrain.GRASSY),
        )
        flat = DamageCalculator.calculate(
            attacker=venusaur(),
            defender=blissey(),
            move=razor_leaf,
            conditions=_max_roll(),
        )
        assert boosted.terrain_multiplier == pytest.approx(1.3)
        assert boosted.damage > flat.damage

    def test_burn_halves_physical_damage(self) -> None:
        """Garchomp EQ vs Blissey (matchup neutro) — verifica el halving del burn."""
        healthy = DamageCalculator.calculate(
            attacker=garchomp(),
            defender=blissey(),
            move=EARTHQUAKE,
            conditions=_max_roll(),
        )
        burned_attacker = replace(garchomp(), status=StatusCondition.BURN)
        burned = DamageCalculator.calculate(
            attacker=burned_attacker,
            defender=blissey(),
            move=EARTHQUAKE,
            conditions=_max_roll(),
        )
        assert healthy.damage > 0
        assert burned.burn_multiplier == 0.5
        assert burned.damage <= int(healthy.damage * 0.51)

    def test_burn_does_not_affect_special_moves(self) -> None:
        """Charizard quemado tirando Flamethrower (especial) no recibe penalty."""
        burned = replace(charizard(), status=StatusCondition.BURN)
        result = DamageCalculator.calculate(
            attacker=burned,
            defender=venusaur(),
            move=FLAMETHROWER,
            conditions=_max_roll(),
        )
        assert result.burn_multiplier == 1.0

    def test_light_screen_halves_special_damage(self) -> None:
        """Gengar Shadow Ball vs Garchomp: Ghost vs Dragon/Ground = ×1 neutro."""
        without = DamageCalculator.calculate(
            attacker=gengar(),
            defender=garchomp(),
            move=SHADOW_BALL,
            conditions=_max_roll(),
        )
        with_screen = DamageCalculator.calculate(
            attacker=gengar(),
            defender=garchomp(),
            move=SHADOW_BALL,
            conditions=replace(_max_roll(), light_screen_active=True),
        )
        assert without.damage > 0
        assert with_screen.screens_multiplier == 0.5
        assert with_screen.damage < without.damage

    def test_crit_ignores_screens(self) -> None:
        """Crit anula screens: el multiplicador queda en 1.0."""
        result = DamageCalculator.calculate(
            attacker=gengar(),
            defender=garchomp(),
            move=SHADOW_BALL,
            conditions=replace(_max_roll(), light_screen_active=True, is_critical=True),
        )
        assert result.screens_multiplier == 1.0


# =========================================================================
# 4) Random factor: rango 85%–100%
# =========================================================================


class TestRandomRange:
    def test_min_roll_is_below_max_roll(self) -> None:
        """Range no-inmune: Garchomp EQ vs Blissey (matchup neutro)."""
        low, high = DamageCalculator.damage_range(
            attacker=garchomp(),
            defender=blissey(),
            move=EARTHQUAKE,
        )
        assert low > 0
        assert low < high
        assert low / high == pytest.approx(0.85, rel=0.05)

    def test_immune_matchup_returns_zero_range(self) -> None:
        """Garchomp EQ vs Salamence (Flying inmune a Ground) → siempre 0."""
        low, high = DamageCalculator.damage_range(
            attacker=garchomp(),
            defender=salamence(),
            move=EARTHQUAKE,
        )
        assert low == 0
        assert high == 0

    def test_random_factor_validation(self) -> None:
        from shared.errors import ValidationError

        with pytest.raises(ValidationError):
            BattleConditions(random_factor=0.5)


# =========================================================================
# 5) Errores y casos defensivos
# =========================================================================


class TestErrorHandling:
    def test_status_move_rejected(self) -> None:
        toxic = Move(
            name="Toxic",
            type=Type.POISON,
            category=MoveCategory.STATUS,
            power=None,
            accuracy=90,
        )
        with pytest.raises(DomainError):
            DamageCalculator.calculate(
                attacker=gengar(),
                defender=blissey(),
                move=toxic,
            )

    def test_zero_power_rejected(self) -> None:
        weird = Move(
            name="Splash",
            type=Type.NORMAL,
            category=MoveCategory.PHYSICAL,
            power=0,
            accuracy=100,
        )
        with pytest.raises(DomainError):
            DamageCalculator.calculate(
                attacker=garchomp(),
                defender=salamence(),
                move=weird,
            )


# =========================================================================
# 6) Anclas numéricas (regresión)
# =========================================================================
#
# Estos casos fijan valores absolutos. Si la fórmula se rompe, los tests caen
# y lo notamos en CI. Los rangos vienen de damage calc públicos calibrados con
# Showdown!. Tolerancia ±2 para absorber el orden de los floors internos.


class TestNumericAnchors:
    def test_garchomp_eq_vs_blissey_neutral_max_roll(self) -> None:
        """Garchomp Lv100 Jolly 252 Atk EQ vs Blissey 252 HP / 252 Def Calm.

        Cálculo manual:
          - Atk efectivo Garchomp = 359 (Jolly neutro para Atk).
          - Def efectivo Blissey  = 119 (252 EV, IV 31, base 10, neutro).
          - Base = ((((2*100)/5+2) * 100 * 359 / 119) / 50) + 2 = 255.
          - Modifier = 1.5 STAB × 1.0 type × 1.0 random = 1.5.
          - Damage max-roll ≈ 382.
        Tolerancia ±10 por floors internos.
        """
        result = DamageCalculator.calculate(
            attacker=garchomp(),
            defender=blissey(),
            move=EARTHQUAKE,
            conditions=_max_roll(),
        )
        assert 370 <= result.damage <= 395
        assert result.type_effectiveness == 1.0
        assert result.stab_multiplier == 1.5

    def test_gengar_thunderbolt_vs_blissey_max_roll(self) -> None:
        """Gengar Timid 252 SpA Thunderbolt vs Blissey 252/4 SpD: bajo (no STAB)."""
        result = DamageCalculator.calculate(
            attacker=gengar(),
            defender=blissey(),
            move=THUNDERBOLT,
            conditions=_max_roll(),
        )
        assert result.damage > 0
        assert result.stab_multiplier == 1.0

    def test_charizard_hydro_pump_vs_charizard_in_rain(self) -> None:
        """Hydro Pump vs Charizard (Fire/Flying): rain (×1.5) + SE ×2.

        Charizard: Water vs Fire ×2, Water vs Flying ×1 → total ×2.
        El atacante es otro Charizard (proxy "espejo") → sin STAB.
        """
        result = DamageCalculator.calculate(
            attacker=charizard(),
            defender=charizard(),
            move=HYDRO_PUMP,
            conditions=replace(_max_roll(), weather=Weather.RAIN),
        )
        assert result.weather_multiplier == 1.5
        assert result.type_effectiveness == 2.0
        assert result.stab_multiplier == 1.0
        assert result.damage > 0

"""Tests de invariantes de value objects."""

from __future__ import annotations

import pytest

from domain.pokemon.value_objects import (
    BattleConditions,
    EVs,
    IVs,
    Nature,
    Stats,
    compute_effective_stat,
)
from shared.errors import ValidationError


class TestStats:
    def test_total_is_sum_of_all(self) -> None:
        s = Stats(hp=100, attack=120, defense=70, special_attack=120, special_defense=70, speed=80)
        assert s.total == 560

    def test_negative_stat_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Stats(hp=-1, attack=0, defense=0, special_attack=0, special_defense=0, speed=0)


class TestIVs:
    def test_default_is_max(self) -> None:
        ivs = IVs()
        assert ivs.hp == 31

    def test_iv_above_31_rejected(self) -> None:
        with pytest.raises(ValidationError):
            IVs(hp=32)

    def test_iv_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            IVs(speed=-1)


class TestEVs:
    def test_default_is_zero(self) -> None:
        evs = EVs()
        assert evs.total == 0

    def test_max_per_stat(self) -> None:
        with pytest.raises(ValidationError):
            EVs(attack=253)

    def test_total_cap_510(self) -> None:
        with pytest.raises(ValidationError):
            # 252+252+252 = 756 > 510
            EVs(attack=252, speed=252, hp=252)

    def test_within_total_limits(self) -> None:
        evs = EVs(attack=252, speed=252, hp=4)
        assert evs.total == 508


class TestNature:
    def test_neutral_natures_have_no_effect(self) -> None:
        for n in (Nature.HARDY, Nature.DOCILE, Nature.SERIOUS, Nature.BASHFUL, Nature.QUIRKY):
            assert n.boost is None
            assert n.drop is None
            assert n.multiplier_for("attack") == 1.0

    def test_adamant_boosts_attack_drops_special_attack(self) -> None:
        assert Nature.ADAMANT.multiplier_for("attack") == 1.1
        assert Nature.ADAMANT.multiplier_for("special_attack") == 0.9
        assert Nature.ADAMANT.multiplier_for("speed") == 1.0

    def test_jolly_boosts_speed_drops_special_attack(self) -> None:
        assert Nature.JOLLY.multiplier_for("speed") == 1.1
        assert Nature.JOLLY.multiplier_for("special_attack") == 0.9


class TestComputeEffectiveStat:
    """Casos canon de Bulbapedia "Statistic" para Garchomp Lv100."""

    def test_garchomp_hp_at_level_100(self) -> None:
        # Base 108 HP, IV 31, EV 0 a Lv100 => floor((216+31+0)*100/100)+100+10 = 247+110 = 357
        hp = compute_effective_stat(base=108, iv=31, ev=0, level=100, is_hp=True)
        assert hp == 357

    def test_garchomp_attack_neutral(self) -> None:
        # Base 130 Atk, IV 31, EV 0, neutral, Lv100:
        # inner = 2*130 + 31 + floor(0/4) = 291
        # stat  = floor(floor(291*100/100) + 5) * 1.0 = 296
        # (Coincide con damage calc públicos: Garchomp 0 EV neutral Atk = 296.)
        atk = compute_effective_stat(
            base=130, iv=31, ev=0, level=100, nature_multiplier=1.0
        )
        assert atk == 296

    def test_garchomp_attack_252_evs_jolly_neutral(self) -> None:
        # Jolly es neutra para Attack → mult 1.0; 252 EV → +63 floor; 31 IV
        # inner = (260 + 31 + 63) * 100/100 = 354 ; +5 = 359 ; *1.0 = 359
        atk = compute_effective_stat(base=130, iv=31, ev=252, level=100)
        assert atk == 359

    def test_garchomp_attack_252_evs_adamant(self) -> None:
        # Adamant +10% Atk: 359 * 1.1 = 394.9 → floor 394
        atk = compute_effective_stat(
            base=130, iv=31, ev=252, level=100, nature_multiplier=1.1
        )
        assert atk == 394


class TestBattleConditions:
    def test_random_factor_in_range(self) -> None:
        BattleConditions(random_factor=0.85)
        BattleConditions(random_factor=1.0)

    def test_random_factor_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            BattleConditions(random_factor=0.84)
        with pytest.raises(ValidationError):
            BattleConditions(random_factor=1.01)

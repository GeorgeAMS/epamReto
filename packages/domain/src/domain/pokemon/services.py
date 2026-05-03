"""Domain services del bounded context Pokémon.

Contiene la **fórmula de daño Gen IX completa** y la **tabla de tipos**.

Diseño deliberado:
- Funciones puras, sin I/O.
- ``DamageCalculator.calculate(...)`` es determinista dado un ``random_factor`` fijo.
- El `calculator_agent` (capa agentes) llama directamente a esta clase para
  garantizar correctness numérico (NO se delega a un LLM).
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.pokemon.entities import Move, Pokemon
from domain.pokemon.value_objects import (
    BattleConditions,
    MoveCategory,
    StatusCondition,
    Terrain,
    Type,
    Weather,
)
from shared.errors import DomainError

# =========================================================================
# Tabla de efectividad de tipos (Gen VI–IX)
# =========================================================================
#
# Lectura: ``TYPE_CHART[attack][defense]`` = multiplicador.
# Codificación compacta — solo se listan multiplicadores ≠ 1.0; el resto se
# infiere como neutro.

_NOT_VERY_EFFECTIVE = 0.5
_SUPER_EFFECTIVE = 2.0
_NO_EFFECT = 0.0

_OVERRIDES: dict[Type, dict[Type, float]] = {
    Type.NORMAL: {
        Type.ROCK: _NOT_VERY_EFFECTIVE,
        Type.GHOST: _NO_EFFECT,
        Type.STEEL: _NOT_VERY_EFFECTIVE,
    },
    Type.FIRE: {
        Type.FIRE: _NOT_VERY_EFFECTIVE,
        Type.WATER: _NOT_VERY_EFFECTIVE,
        Type.GRASS: _SUPER_EFFECTIVE,
        Type.ICE: _SUPER_EFFECTIVE,
        Type.BUG: _SUPER_EFFECTIVE,
        Type.ROCK: _NOT_VERY_EFFECTIVE,
        Type.DRAGON: _NOT_VERY_EFFECTIVE,
        Type.STEEL: _SUPER_EFFECTIVE,
    },
    Type.WATER: {
        Type.FIRE: _SUPER_EFFECTIVE,
        Type.WATER: _NOT_VERY_EFFECTIVE,
        Type.GRASS: _NOT_VERY_EFFECTIVE,
        Type.GROUND: _SUPER_EFFECTIVE,
        Type.ROCK: _SUPER_EFFECTIVE,
        Type.DRAGON: _NOT_VERY_EFFECTIVE,
    },
    Type.ELECTRIC: {
        Type.WATER: _SUPER_EFFECTIVE,
        Type.ELECTRIC: _NOT_VERY_EFFECTIVE,
        Type.GRASS: _NOT_VERY_EFFECTIVE,
        Type.GROUND: _NO_EFFECT,
        Type.FLYING: _SUPER_EFFECTIVE,
        Type.DRAGON: _NOT_VERY_EFFECTIVE,
    },
    Type.GRASS: {
        Type.FIRE: _NOT_VERY_EFFECTIVE,
        Type.WATER: _SUPER_EFFECTIVE,
        Type.GRASS: _NOT_VERY_EFFECTIVE,
        Type.POISON: _NOT_VERY_EFFECTIVE,
        Type.GROUND: _SUPER_EFFECTIVE,
        Type.FLYING: _NOT_VERY_EFFECTIVE,
        Type.BUG: _NOT_VERY_EFFECTIVE,
        Type.ROCK: _SUPER_EFFECTIVE,
        Type.DRAGON: _NOT_VERY_EFFECTIVE,
        Type.STEEL: _NOT_VERY_EFFECTIVE,
    },
    Type.ICE: {
        Type.FIRE: _NOT_VERY_EFFECTIVE,
        Type.WATER: _NOT_VERY_EFFECTIVE,
        Type.GRASS: _SUPER_EFFECTIVE,
        Type.ICE: _NOT_VERY_EFFECTIVE,
        Type.GROUND: _SUPER_EFFECTIVE,
        Type.FLYING: _SUPER_EFFECTIVE,
        Type.DRAGON: _SUPER_EFFECTIVE,
        Type.STEEL: _NOT_VERY_EFFECTIVE,
    },
    Type.FIGHTING: {
        Type.NORMAL: _SUPER_EFFECTIVE,
        Type.ICE: _SUPER_EFFECTIVE,
        Type.POISON: _NOT_VERY_EFFECTIVE,
        Type.FLYING: _NOT_VERY_EFFECTIVE,
        Type.PSYCHIC: _NOT_VERY_EFFECTIVE,
        Type.BUG: _NOT_VERY_EFFECTIVE,
        Type.ROCK: _SUPER_EFFECTIVE,
        Type.GHOST: _NO_EFFECT,
        Type.DARK: _SUPER_EFFECTIVE,
        Type.STEEL: _SUPER_EFFECTIVE,
        Type.FAIRY: _NOT_VERY_EFFECTIVE,
    },
    Type.POISON: {
        Type.GRASS: _SUPER_EFFECTIVE,
        Type.POISON: _NOT_VERY_EFFECTIVE,
        Type.GROUND: _NOT_VERY_EFFECTIVE,
        Type.ROCK: _NOT_VERY_EFFECTIVE,
        Type.GHOST: _NOT_VERY_EFFECTIVE,
        Type.STEEL: _NO_EFFECT,
        Type.FAIRY: _SUPER_EFFECTIVE,
    },
    Type.GROUND: {
        Type.FIRE: _SUPER_EFFECTIVE,
        Type.ELECTRIC: _SUPER_EFFECTIVE,
        Type.GRASS: _NOT_VERY_EFFECTIVE,
        Type.POISON: _SUPER_EFFECTIVE,
        Type.FLYING: _NO_EFFECT,
        Type.BUG: _NOT_VERY_EFFECTIVE,
        Type.ROCK: _SUPER_EFFECTIVE,
        Type.STEEL: _SUPER_EFFECTIVE,
    },
    Type.FLYING: {
        Type.ELECTRIC: _NOT_VERY_EFFECTIVE,
        Type.GRASS: _SUPER_EFFECTIVE,
        Type.FIGHTING: _SUPER_EFFECTIVE,
        Type.BUG: _SUPER_EFFECTIVE,
        Type.ROCK: _NOT_VERY_EFFECTIVE,
        Type.STEEL: _NOT_VERY_EFFECTIVE,
    },
    Type.PSYCHIC: {
        Type.FIGHTING: _SUPER_EFFECTIVE,
        Type.POISON: _SUPER_EFFECTIVE,
        Type.PSYCHIC: _NOT_VERY_EFFECTIVE,
        Type.DARK: _NO_EFFECT,
        Type.STEEL: _NOT_VERY_EFFECTIVE,
    },
    Type.BUG: {
        Type.FIRE: _NOT_VERY_EFFECTIVE,
        Type.GRASS: _SUPER_EFFECTIVE,
        Type.FIGHTING: _NOT_VERY_EFFECTIVE,
        Type.POISON: _NOT_VERY_EFFECTIVE,
        Type.FLYING: _NOT_VERY_EFFECTIVE,
        Type.PSYCHIC: _SUPER_EFFECTIVE,
        Type.GHOST: _NOT_VERY_EFFECTIVE,
        Type.DARK: _SUPER_EFFECTIVE,
        Type.STEEL: _NOT_VERY_EFFECTIVE,
        Type.FAIRY: _NOT_VERY_EFFECTIVE,
    },
    Type.ROCK: {
        Type.FIRE: _SUPER_EFFECTIVE,
        Type.ICE: _SUPER_EFFECTIVE,
        Type.FIGHTING: _NOT_VERY_EFFECTIVE,
        Type.GROUND: _NOT_VERY_EFFECTIVE,
        Type.FLYING: _SUPER_EFFECTIVE,
        Type.BUG: _SUPER_EFFECTIVE,
        Type.STEEL: _NOT_VERY_EFFECTIVE,
    },
    Type.GHOST: {
        Type.NORMAL: _NO_EFFECT,
        Type.PSYCHIC: _SUPER_EFFECTIVE,
        Type.GHOST: _SUPER_EFFECTIVE,
        Type.DARK: _NOT_VERY_EFFECTIVE,
    },
    Type.DRAGON: {
        Type.DRAGON: _SUPER_EFFECTIVE,
        Type.STEEL: _NOT_VERY_EFFECTIVE,
        Type.FAIRY: _NO_EFFECT,
    },
    Type.DARK: {
        Type.FIGHTING: _NOT_VERY_EFFECTIVE,
        Type.PSYCHIC: _SUPER_EFFECTIVE,
        Type.GHOST: _SUPER_EFFECTIVE,
        Type.DARK: _NOT_VERY_EFFECTIVE,
        Type.FAIRY: _NOT_VERY_EFFECTIVE,
    },
    Type.STEEL: {
        Type.FIRE: _NOT_VERY_EFFECTIVE,
        Type.WATER: _NOT_VERY_EFFECTIVE,
        Type.ELECTRIC: _NOT_VERY_EFFECTIVE,
        Type.ICE: _SUPER_EFFECTIVE,
        Type.ROCK: _SUPER_EFFECTIVE,
        Type.STEEL: _NOT_VERY_EFFECTIVE,
        Type.FAIRY: _SUPER_EFFECTIVE,
    },
    Type.FAIRY: {
        Type.FIRE: _NOT_VERY_EFFECTIVE,
        Type.FIGHTING: _SUPER_EFFECTIVE,
        Type.POISON: _NOT_VERY_EFFECTIVE,
        Type.DRAGON: _SUPER_EFFECTIVE,
        Type.DARK: _SUPER_EFFECTIVE,
        Type.STEEL: _NOT_VERY_EFFECTIVE,
    },
}


class TypeEffectiveness:
    """Servicio de dominio: efectividad entre tipos.

    Consultas O(1) sobre tabla canon de Gen IX.
    """

    @staticmethod
    def single(attack: Type, defense: Type) -> float:
        """Multiplicador de un tipo atacante contra un tipo defensor."""
        return _OVERRIDES.get(attack, {}).get(defense, 1.0)

    @classmethod
    def vs_pokemon(cls, attack: Type, defender: Pokemon) -> float:
        """Multiplicador combinado contra el tipo (mono/dual) del Pokémon defensor.

        En Gen IX, si el defensor está terastalizado, su tipo a efectos
        defensivos es **únicamente** su `tera_type` (no los originales).
        """
        defending_types: tuple[Type, ...]
        if defender.is_terastalized and defender.tera_type is not None:
            defending_types = (defender.tera_type,)
        else:
            defending_types = defender.types

        result = 1.0
        for t in defending_types:
            result *= cls.single(attack, t)
        return result


# =========================================================================
# Damage Calculator — fórmula Gen IX
# =========================================================================
#
# Fórmula canonical (Bulbapedia "Damage"):
#
#   damage = ((((2*L)/5 + 2) * Power * A/D) / 50 + 2) * Modifier
#
# donde Modifier es la multiplicación de:
#   targets * pb * weather * crit * random * stab * type * burn * other
#
# Notas Gen IX que aplicamos:
# - Crit = 1.5 (era 2.0 en Gen ≤ V).
# - Burn divide solo el daño físico (Atk), no el especial; ignorado por Guts/Facade.
# - STAB = 1.5 (2.0 con Adaptability; reglas especiales con Tera).
# - Random (R) se modela como `random_factor` ∈ [0.85, 1.0], no se llama RNG aquí.


@dataclass(frozen=True)
class DamageResult:
    """Resultado del cálculo de daño con todos los multiplicadores aplicados.

    Mantenemos los componentes para que el `verifier_agent` y la UI puedan
    explicar al usuario por qué un golpe pegó X (ej. "STAB 1.5 × Super 2.0").
    """

    damage: int
    base_damage: int                  # Antes del modificador final
    type_effectiveness: float
    stab_multiplier: float
    crit_multiplier: float
    weather_multiplier: float
    terrain_multiplier: float
    burn_multiplier: float
    screens_multiplier: float
    random_factor: float
    is_immune: bool                   # type_effectiveness == 0
    notes: tuple[str, ...] = ()

    @property
    def percent_of_max_hp(self) -> float | None:
        """Se rellena externamente; se deja como propiedad para el reporter."""
        return None


class DamageCalculator:
    """Implementación pura de la fórmula de daño Gen IX.

    Uso típico::

        result = DamageCalculator.calculate(
            attacker=garchomp,
            defender=salamence,
            move=ice_fang,
            conditions=BattleConditions(random_factor=1.0),
        )
        print(result.damage, result.type_effectiveness)
    """

    @staticmethod
    def calculate(
        *,
        attacker: Pokemon,
        defender: Pokemon,
        move: Move,
        conditions: BattleConditions | None = None,
    ) -> DamageResult:
        if move.category == MoveCategory.STATUS:
            raise DomainError(
                "No se puede calcular daño de un move de categoría STATUS",
                details={"move": move.name},
            )
        if move.power is None or move.power <= 0:
            raise DomainError(
                "Move sin power positivo no puede calcularse aquí (caso especial)",
                details={"move": move.name, "power": move.power},
            )

        cond = conditions or BattleConditions()

        # --- Stats efectivos con stages -----------------------------------
        atk_stats = attacker.effective_stats()
        def_stats = defender.effective_stats()

        if move.category == MoveCategory.PHYSICAL:
            attack_stat = atk_stats.attack * attacker.stage_multiplier("attack")
            defense_stat = def_stats.defense * defender.stage_multiplier("defense")
        else:  # SPECIAL
            attack_stat = atk_stats.special_attack * attacker.stage_multiplier("special_attack")
            defense_stat = def_stats.special_defense * defender.stage_multiplier(
                "special_defense"
            )

        # --- Daño base ----------------------------------------------------
        # Damage = ((((2*L)/5 + 2) * Power * A/D) / 50 + 2)
        level_term = (2 * attacker.level) // 5 + 2
        base = (level_term * move.power * attack_stat) / max(defense_stat, 1.0)
        base = base / 50 + 2
        base_damage = int(base)

        # --- Modificadores ------------------------------------------------
        # 1) Targets (dobles spread): aplicamos solo cuando la condición lo indique.
        targets_mult = 0.75 if cond.is_doubles_spread else 1.0

        # 2) Weather
        weather_mult = _weather_multiplier(move.type, cond.weather)

        # 3) Crit
        crit_mult = 1.5 if cond.is_critical else 1.0

        # 4) STAB
        stab_mult = _stab_multiplier(attacker, move)

        # 5) Type effectiveness
        type_mult = TypeEffectiveness.vs_pokemon(move.type, defender)

        # 6) Burn (físico, salvo Guts/Facade — para hackathon ignoramos Guts).
        burn_mult = 1.0
        if (
            attacker.status == StatusCondition.BURN
            and move.category == MoveCategory.PHYSICAL
            and move.name.lower() != "facade"
        ):
            burn_mult = 0.5

        # 7) Terrain (solo si el atacante está grounded)
        terrain_mult = 1.0
        if cond.attacker_is_grounded:
            terrain_mult = _terrain_multiplier(move.type, cond.terrain)

        # 8) Pantallas (Reflect / Light Screen / Aurora Veil)
        screens_mult = _screens_multiplier(move, cond, is_critical=cond.is_critical)

        # 9) Random factor
        random_mult = cond.random_factor

        # --- Aplicación canónica del modificador --------------------------
        # Bulbapedia detalla que cada paso aplica `floor` en el motor real;
        # mantenemos floats y solo redondeamos al final para no acumular error
        # en exceso (suficiente para validación didáctica).
        modifier = (
            targets_mult
            * weather_mult
            * crit_mult
            * random_mult
            * stab_mult
            * type_mult
            * burn_mult
            * terrain_mult
            * screens_mult
        )

        damage = max(0, int(base_damage * modifier))
        # Regla canon: si el move pega y type_eff > 0, mínimo daño = 1.
        is_immune = type_mult == 0.0
        weather_blocks = weather_mult == 0.0  # Heavy Rain vs Fire / Harsh Sun vs Water
        if not is_immune and not weather_blocks and damage == 0 and base_damage > 0:
            damage = 1

        notes: list[str] = []
        if is_immune:
            notes.append("Inmune por tipo (×0).")
        if stab_mult > 1.0:
            notes.append(f"STAB ×{stab_mult:g}.")
        if type_mult > 1.0:
            notes.append(f"Super efectivo ×{type_mult:g}.")
        elif 0.0 < type_mult < 1.0:
            notes.append(f"Poco efectivo ×{type_mult:g}.")
        if crit_mult > 1.0:
            notes.append("Crítico ×1.5.")
        if weather_mult != 1.0:
            notes.append(f"Clima ×{weather_mult:g}.")
        if terrain_mult != 1.0:
            notes.append(f"Terreno ×{terrain_mult:g}.")
        if burn_mult != 1.0:
            notes.append("Quemadura ×0.5.")
        if screens_mult != 1.0:
            notes.append(f"Pantallas ×{screens_mult:g}.")

        return DamageResult(
            damage=damage,
            base_damage=base_damage,
            type_effectiveness=type_mult,
            stab_multiplier=stab_mult,
            crit_multiplier=crit_mult,
            weather_multiplier=weather_mult,
            terrain_multiplier=terrain_mult,
            burn_multiplier=burn_mult,
            screens_multiplier=screens_mult,
            random_factor=random_mult,
            is_immune=is_immune,
            notes=tuple(notes),
        )

    @staticmethod
    def damage_range(
        *,
        attacker: Pokemon,
        defender: Pokemon,
        move: Move,
        conditions: BattleConditions | None = None,
    ) -> tuple[int, int]:
        """Devuelve ``(min_damage, max_damage)`` cubriendo random ∈ [0.85, 1.0]."""
        base_cond = conditions or BattleConditions()
        from dataclasses import replace as _replace

        low = DamageCalculator.calculate(
            attacker=attacker,
            defender=defender,
            move=move,
            conditions=_replace(base_cond, random_factor=0.85),
        )
        high = DamageCalculator.calculate(
            attacker=attacker,
            defender=defender,
            move=move,
            conditions=_replace(base_cond, random_factor=1.0),
        )
        return low.damage, high.damage


# --- Helpers internos ----------------------------------------------------


def _stab_multiplier(attacker: Pokemon, move: Move) -> float:
    """Calcula STAB (Same-Type Attack Bonus) considerando Adaptability y Tera.

    Reglas Gen IX (resumen):
    - Sin tera: STAB = 1.5 si el move comparte tipo con uno de los originales.
      Adaptability lo sube a 2.0.
    - Tera con tipo distinto al original:
        * Move del tipo original → STAB 1.5 (se mantiene).
        * Move del tipo Tera     → STAB 1.5.
        * Si Tera coincide con original Y el move es ese tipo → STAB 2.0.
    - Adaptability no se acumula con la regla anterior; mantenemos modelo
      conservador apto para casi todos los casos competitivos del set típico.
    """
    base_types = set(attacker.types)
    has_base_stab = move.type in base_types

    if attacker.is_terastalized and attacker.tera_type is not None:
        is_tera_move = move.type == attacker.tera_type
        tera_matches_original = attacker.tera_type in base_types

        if is_tera_move and tera_matches_original:
            return 2.0  # Tera + tipo original coincidente
        if is_tera_move or has_base_stab:
            return 2.0 if attacker.ability.boosts_stab_to_2x else 1.5
        return 1.0

    if has_base_stab:
        return 2.0 if attacker.ability.boosts_stab_to_2x else 1.5
    return 1.0


def _weather_multiplier(move_type: Type, weather: Weather) -> float:
    """Boost/debuff por clima sobre el tipo del move."""
    if weather in (Weather.SUN, Weather.HARSH_SUN):
        if move_type == Type.FIRE:
            return 1.5
        if move_type == Type.WATER:
            return 0.5 if weather == Weather.SUN else 0.0  # Harsh Sun bloquea agua
    if weather in (Weather.RAIN, Weather.HEAVY_RAIN):
        if move_type == Type.WATER:
            return 1.5
        if move_type == Type.FIRE:
            return 0.5 if weather == Weather.RAIN else 0.0  # Heavy Rain bloquea fuego
    return 1.0


def _terrain_multiplier(move_type: Type, terrain: Terrain) -> float:
    """Modificador del terreno sobre el move (atacante grounded)."""
    if terrain == Terrain.ELECTRIC and move_type == Type.ELECTRIC:
        return 1.3
    if terrain == Terrain.GRASSY and move_type == Type.GRASS:
        return 1.3
    if terrain == Terrain.PSYCHIC and move_type == Type.PSYCHIC:
        return 1.3
    if terrain == Terrain.MISTY and move_type == Type.DRAGON:
        return 0.5
    return 1.0


def _screens_multiplier(
    move: Move,
    cond: BattleConditions,
    *,
    is_critical: bool,
) -> float:
    """Reflect/Light Screen/Aurora Veil reducen 50% (singles); ignoradas si crit."""
    if is_critical:
        return 1.0
    if move.category == MoveCategory.PHYSICAL:
        if cond.reflect_active or cond.aurora_veil_active:
            return 0.5
    elif move.category == MoveCategory.SPECIAL:
        if cond.light_screen_active or cond.aurora_veil_active:
            return 0.5
    return 1.0


__all__ = ["DamageCalculator", "DamageResult", "TypeEffectiveness"]

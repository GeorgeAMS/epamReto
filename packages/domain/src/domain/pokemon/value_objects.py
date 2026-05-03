"""Value objects del bounded context Pokémon (Gen IX).

Todos los tipos viven aquí: enums (Type, MoveCategory, Weather, Terrain,
StatusCondition, Nature) y dataclasses inmutables (Stats, EVs, IVs,
BattleConditions). La función ``compute_effective_stat`` aplica la fórmula
canon de Bulbapedia (Statistic) — usada también por ``Pokemon.effective_stats``.

Reglas duras:
- Sin imports externos (sólo ``shared.errors``).
- Todas las invariantes se validan en ``__post_init__`` con ``ValidationError``.
- Inmutables (``frozen=True``) → reusables como claves de cache.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from shared.errors import ValidationError

# ===========================================================================
# 1) Tipos
# ===========================================================================


class Type(str, Enum):
    """Los 18 tipos canon (Gen VI–IX).

    El ``.value`` es lower-case para alinear con PokéAPI ("normal", "fire", ...).
    El servicio ``TypeEffectiveness`` define la matriz completa.
    """

    NORMAL = "normal"
    FIRE = "fire"
    WATER = "water"
    ELECTRIC = "electric"
    GRASS = "grass"
    ICE = "ice"
    FIGHTING = "fighting"
    POISON = "poison"
    GROUND = "ground"
    FLYING = "flying"
    PSYCHIC = "psychic"
    BUG = "bug"
    ROCK = "rock"
    GHOST = "ghost"
    DRAGON = "dragon"
    DARK = "dark"
    STEEL = "steel"
    FAIRY = "fairy"


class MoveCategory(str, Enum):
    """Categoría del movimiento (Gen IV+: el split físico/especial)."""

    PHYSICAL = "physical"
    SPECIAL = "special"
    STATUS = "status"


class Weather(str, Enum):
    """Climas activos en batalla.

    ``HARSH_SUN`` y ``HEAVY_RAIN`` son las versiones primal/extreme (Gen VI+):
    bloquean Water/Fire respectivamente y son las que usa el verifier para
    sanity check.
    """

    CLEAR = "clear"
    SUN = "sun"
    RAIN = "rain"
    SAND = "sand"
    HAIL = "hail"
    SNOW = "snow"
    HARSH_SUN = "harsh_sun"
    HEAVY_RAIN = "heavy_rain"


class Terrain(str, Enum):
    """Terrenos (Gen VI+). Solo afectan a Pokémon ``grounded``."""

    NONE = "none"
    ELECTRIC = "electric"
    GRASSY = "grassy"
    PSYCHIC = "psychic"
    MISTY = "misty"


class StatusCondition(str, Enum):
    """Condiciones de estado mayor (un único slot por Pokémon)."""

    NONE = "none"
    BURN = "burn"
    POISON = "poison"
    BAD_POISON = "bad_poison"
    PARALYSIS = "paralysis"
    SLEEP = "sleep"
    FREEZE = "freeze"


# ===========================================================================
# 2) Naturaleza (25 entries, +10%/-10% sobre dos stats)
# ===========================================================================
#
# Convención: cada miembro lleva (boost_stat, drop_stat) usando los nombres
# canónicos de campo (snake_case) que también usan ``Stats`` y ``EVs``:
#   "attack" | "defense" | "special_attack" | "special_defense" | "speed"
# Las cinco neutras (HARDY, DOCILE, SERIOUS, BASHFUL, QUIRKY) llevan (None, None).


_StatName = str  # alias para legibilidad — se valida en runtime


_NATURE_AFFECTED_STATS: frozenset[str] = frozenset(
    {"attack", "defense", "special_attack", "special_defense", "speed"}
)


class Nature(Enum):
    """25 naturalezas canon Gen III+.

    ``boost`` y ``drop`` son los nombres del stat afectado o ``None`` para neutras.
    """

    # Neutras (no afectan stats)
    HARDY = (None, None)
    DOCILE = (None, None)
    SERIOUS = (None, None)
    BASHFUL = (None, None)
    QUIRKY = (None, None)

    # +Atk
    LONELY = ("attack", "defense")
    BRAVE = ("attack", "speed")
    ADAMANT = ("attack", "special_attack")
    NAUGHTY = ("attack", "special_defense")

    # +Def
    BOLD = ("defense", "attack")
    RELAXED = ("defense", "speed")
    IMPISH = ("defense", "special_attack")
    LAX = ("defense", "special_defense")

    # +Speed
    TIMID = ("speed", "attack")
    HASTY = ("speed", "defense")
    JOLLY = ("speed", "special_attack")
    NAIVE = ("speed", "special_defense")

    # +SpA
    MODEST = ("special_attack", "attack")
    MILD = ("special_attack", "defense")
    QUIET = ("special_attack", "speed")
    RASH = ("special_attack", "special_defense")

    # +SpD
    CALM = ("special_defense", "attack")
    GENTLE = ("special_defense", "defense")
    SASSY = ("special_defense", "speed")
    CAREFUL = ("special_defense", "special_attack")

    boost: _StatName | None
    drop: _StatName | None

    def __init__(self, boost: _StatName | None, drop: _StatName | None) -> None:
        self.boost = boost
        self.drop = drop

    def multiplier_for(self, stat: _StatName) -> float:
        """Devuelve 1.1 si la naturaleza sube ``stat``, 0.9 si lo baja, 1.0 si neutro.

        ``stat`` debe ser uno de los nombres válidos
        (``attack/defense/special_attack/special_defense/speed``).
        ``hp`` siempre devuelve 1.0 (las naturalezas no afectan HP).
        """
        if stat == "hp":
            return 1.0
        if self.boost == stat:
            return 1.1
        if self.drop == stat:
            return 0.9
        return 1.0


# ===========================================================================
# 3) Stats
# ===========================================================================
#
# Mantenemos `Stats` simple: contenedor inmutable con la suma BST (``total``).
# La aritmética con nature/EVs/IVs se hace en ``compute_effective_stat`` para
# poder probarlo aislado.


_STAT_FIELDS: tuple[str, ...] = (
    "hp",
    "attack",
    "defense",
    "special_attack",
    "special_defense",
    "speed",
)


@dataclass(frozen=True)
class Stats:
    """Tupla de stats (HP, Atk, Def, SpA, SpD, Spe).

    Se usa tanto para *base stats* (canon) como para *effective stats*
    (post nature + IV + EV + level). Los stages NO se aplican aquí: el
    ``DamageCalculator`` los aplica explícitamente con ``stage_multiplier``.
    """

    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int

    def __post_init__(self) -> None:
        for name in _STAT_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, int):
                raise ValidationError(
                    f"Stat `{name}` debe ser entero",
                    details={"stat": name, "value": value},
                )
            if value < 0:
                raise ValidationError(
                    f"Stat `{name}` no puede ser negativo",
                    details={"stat": name, "value": value},
                )

    @property
    def total(self) -> int:
        """BST — Base Stat Total (suma de los seis)."""
        return (
            self.hp
            + self.attack
            + self.defense
            + self.special_attack
            + self.special_defense
            + self.speed
        )


# ===========================================================================
# 4) IVs / EVs
# ===========================================================================


_MAX_IV = 31
_MAX_EV_PER_STAT = 252
_MAX_EV_TOTAL = 510


@dataclass(frozen=True)
class IVs:
    """Individual Values (0–31). Default = 31 (perfectos)."""

    hp: int = _MAX_IV
    attack: int = _MAX_IV
    defense: int = _MAX_IV
    special_attack: int = _MAX_IV
    special_defense: int = _MAX_IV
    speed: int = _MAX_IV

    def __post_init__(self) -> None:
        for name in _STAT_FIELDS:
            value = getattr(self, name)
            if value < 0 or value > _MAX_IV:
                raise ValidationError(
                    f"IV `{name}` fuera de rango [0, {_MAX_IV}]",
                    details={"stat": name, "value": value, "max": _MAX_IV},
                )


@dataclass(frozen=True)
class EVs:
    """Effort Values. Cap por stat = 252; suma global ≤ 510."""

    hp: int = 0
    attack: int = 0
    defense: int = 0
    special_attack: int = 0
    special_defense: int = 0
    speed: int = 0

    def __post_init__(self) -> None:
        for name in _STAT_FIELDS:
            value = getattr(self, name)
            if value < 0 or value > _MAX_EV_PER_STAT:
                raise ValidationError(
                    f"EV `{name}` fuera de rango [0, {_MAX_EV_PER_STAT}]",
                    details={"stat": name, "value": value, "max": _MAX_EV_PER_STAT},
                )
        total = self.total
        if total > _MAX_EV_TOTAL:
            raise ValidationError(
                f"EV total {total} excede el cap {_MAX_EV_TOTAL}",
                details={"total": total, "cap": _MAX_EV_TOTAL},
            )

    @property
    def total(self) -> int:
        return (
            self.hp
            + self.attack
            + self.defense
            + self.special_attack
            + self.special_defense
            + self.speed
        )


# Mantengo aliases EV/IV en singular por si llegan a leer así desde docs externas.
EV = EVs
IV = IVs


# ===========================================================================
# 5) Fórmula canónica de stat efectivo (Bulbapedia "Statistic", Gen III+)
# ===========================================================================
#
# HP    = floor((2*Base + IV + floor(EV/4)) * Level/100) + Level + 10
# Other = floor((floor((2*Base + IV + floor(EV/4)) * Level/100) + 5) * Nature)
#
# Detalle: ``floor`` se aplica DENTRO del paréntesis (al producto level/100)
# y de NUEVO sobre el valor naturado para preservar enteros (Showdown! coincide).


def compute_effective_stat(
    *,
    base: int,
    iv: int,
    ev: int,
    level: int,
    nature_multiplier: float = 1.0,
    is_hp: bool = False,
) -> int:
    """Calcula el stat efectivo de un Pokémon.

    Args:
        base: Base stat del Pokémon (0–255).
        iv: Individual value (0–31).
        ev: Effort value (0–252) — sólo se cuenta ``floor(ev/4)``.
        level: Nivel (1–100).
        nature_multiplier: 1.1 / 1.0 / 0.9 según ``Nature.multiplier_for``.
            Se ignora si ``is_hp=True`` (HP nunca se ve afectado por naturaleza).
        is_hp: Activa la fórmula HP (sin nature, +Level+10 al final).

    Returns:
        Valor entero del stat efectivo.

    Raises:
        ValidationError: si los parámetros caen fuera de rango.
    """
    if not 1 <= level <= 100:
        raise ValidationError(
            "Level fuera de rango [1, 100]",
            details={"level": level},
        )
    if not 0 <= iv <= _MAX_IV:
        raise ValidationError(
            "IV fuera de rango [0, 31]",
            details={"iv": iv},
        )
    if not 0 <= ev <= _MAX_EV_PER_STAT:
        raise ValidationError(
            "EV fuera de rango [0, 252]",
            details={"ev": ev},
        )
    if base < 0:
        raise ValidationError(
            "Base stat no puede ser negativo",
            details={"base": base},
        )

    inner = (2 * base + iv + (ev // 4)) * level // 100

    if is_hp:
        return inner + level + 10

    return int((inner + 5) * nature_multiplier)


# ===========================================================================
# 6) BattleConditions — todos los modificadores externos al duelo
# ===========================================================================


_RANDOM_FACTOR_MIN = 0.85
_RANDOM_FACTOR_MAX = 1.0


@dataclass(frozen=True)
class BattleConditions:
    """Modificadores externos al cálculo de daño.

    El ``random_factor`` simula el roll Gen IX en [0.85, 1.0]. Lo fijamos
    como input para que el ``DamageCalculator`` sea determinista (criterio
    de correctness; el rango se cubre con ``DamageCalculator.damage_range``).
    """

    random_factor: float = 1.0
    is_critical: bool = False
    is_doubles_spread: bool = False
    weather: Weather = Weather.CLEAR
    terrain: Terrain = Terrain.NONE
    attacker_is_grounded: bool = True
    reflect_active: bool = False
    light_screen_active: bool = False
    aurora_veil_active: bool = False

    def __post_init__(self) -> None:
        if not _RANDOM_FACTOR_MIN <= self.random_factor <= _RANDOM_FACTOR_MAX:
            raise ValidationError(
                "random_factor debe estar en [0.85, 1.0]",
                details={
                    "random_factor": self.random_factor,
                    "min": _RANDOM_FACTOR_MIN,
                    "max": _RANDOM_FACTOR_MAX,
                },
            )


# ===========================================================================
# Re-exports
# ===========================================================================

__all__ = [
    "EV",
    "IV",
    "BattleConditions",
    "EVs",
    "IVs",
    "MoveCategory",
    "Nature",
    "Stats",
    "StatusCondition",
    "Terrain",
    "Type",
    "Weather",
    "compute_effective_stat",
]

"""Bounded context: Pokémon (entidades, value objects, fórmula de daño Gen IX).

Re-exports estables. La regla de oro: nadie fuera del dominio debería tener
que importar submódulos directamente — basta con ``from domain.pokemon import ...``.
"""

from domain.pokemon.entities import Ability, Move, Pokemon
from domain.pokemon.services import (
    DamageCalculator,
    DamageResult,
    TypeEffectiveness,
)
from domain.pokemon.value_objects import (
    EV,
    IV,
    BattleConditions,
    EVs,
    IVs,
    MoveCategory,
    Nature,
    Stats,
    StatusCondition,
    Terrain,
    Type,
    Weather,
    compute_effective_stat,
)

__all__ = [
    "EV",
    "IV",
    "Ability",
    "BattleConditions",
    "DamageCalculator",
    "DamageResult",
    "EVs",
    "IVs",
    "Move",
    "MoveCategory",
    "Nature",
    "Pokemon",
    "Stats",
    "StatusCondition",
    "Terrain",
    "Type",
    "TypeEffectiveness",
    "Weather",
    "compute_effective_stat",
]

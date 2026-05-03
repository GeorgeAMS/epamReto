"""Entidades del bounded context Pokémon: ``Pokemon``, ``Move``, ``Ability``.

Todas inmutables (``frozen=True``). Las operaciones derivadas
(``effective_stats``, ``stage_multiplier``) son funciones puras sobre los
campos del propio objeto.

Por qué dataclasses (no Pydantic):
- El dominio NO debe acoplarse a Pydantic (regla dura del proyecto).
- ``frozen=True`` + ``__post_init__`` da invariantes suficientes para los
  tests del damage calculator.
- ``dataclasses.replace`` permite construir variantes (Tera, status) sin
  mutaciones que rompan razonamiento.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.pokemon.value_objects import (
    EVs,
    IVs,
    MoveCategory,
    Nature,
    Stats,
    StatusCondition,
    Type,
    compute_effective_stat,
)
from shared.errors import ValidationError

# ===========================================================================
# Ability
# ===========================================================================


@dataclass(frozen=True)
class Ability:
    """Habilidad del Pokémon.

    Solo modelamos el subconjunto relevante para el cálculo de daño Día 1:
    - ``boosts_stab_to_2x`` cubre Adaptability.
    El resto (Levitate, Lightning Rod, etc.) llega en fases posteriores como
    flags adicionales o estrategia de tablas externas — sin romper esta API.
    """

    name: str
    description: str = ""
    boosts_stab_to_2x: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError(
                "Ability requiere `name` no vacío",
                details={"name": self.name},
            )


# ===========================================================================
# Move
# ===========================================================================


@dataclass(frozen=True)
class Move:
    """Movimiento (move) del Pokémon.

    ``power`` puede ser ``None`` para moves de status (Toxic, Spore...).
    El ``DamageCalculator`` rechaza moves STATUS o con power 0 con un
    ``DomainError`` explícito (los tests lo verifican).
    """

    name: str
    type: Type
    category: MoveCategory
    power: int | None = None
    accuracy: int | None = None
    pp: int = 0
    priority: int = 0
    makes_contact: bool = False
    is_biting: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError(
                "Move requiere `name` no vacío",
                details={"name": self.name},
            )
        if self.accuracy is not None and not 0 <= self.accuracy <= 100:
            raise ValidationError(
                "Move accuracy fuera de rango [0, 100]",
                details={"name": self.name, "accuracy": self.accuracy},
            )
        if self.pp < 0:
            raise ValidationError(
                "Move pp no puede ser negativo",
                details={"name": self.name, "pp": self.pp},
            )


# ===========================================================================
# Pokemon
# ===========================================================================
#
# Los stages competitivos (-6..+6) se modelan como cinco campos individuales
# en lugar de un dict para mantener la dataclass realmente inmutable y typeada.
# El DamageCalculator solo necesita atk/def/spa/spd; ``speed_stage`` queda para
# cuando el strategy_agent necesite calcular outspeeds.

_STAGE_BOUND = 6
_STAGE_FIELDS: tuple[str, ...] = (
    "attack",
    "defense",
    "special_attack",
    "special_defense",
    "speed",
)


def _stage_to_multiplier(stage: int) -> float:
    """Tabla canon de stages (Gen III+).

    ±6 stages aplica (8/2)=4× o 2/8=0.25× sobre el stat. Para HP no hay stages.
    """
    stage = max(-_STAGE_BOUND, min(_STAGE_BOUND, stage))
    if stage >= 0:
        return (2 + stage) / 2.0
    return 2.0 / (2 + abs(stage))


@dataclass(frozen=True)
class Pokemon:
    """Pokémon configurado y listo para batalla.

    Campos opcionales típicos:
    - ``status``: condición mayor (afecta cálculos: BURN ×0.5 al daño físico).
    - ``is_terastalized`` + ``tera_type``: Gen IX. El `TypeEffectiveness`
      sustituye el tipo defensivo cuando ``is_terastalized=True``.
    - ``*_stage``: stages competitivos -6..+6 por stat.
    """

    name: str
    types: tuple[Type, ...]
    base_stats: Stats
    ability: Ability
    level: int = 50
    nature: Nature = Nature.HARDY
    # ``default_factory`` evita compartir la misma instancia EV/IV entre Pokémon
    # (las dataclasses son frozen, pero seguir la convención RUF009 es más sano).
    evs: EVs = field(default_factory=EVs)
    ivs: IVs = field(default_factory=IVs)
    status: StatusCondition = StatusCondition.NONE
    is_terastalized: bool = False
    tera_type: Type | None = None
    attack_stage: int = 0
    defense_stage: int = 0
    special_attack_stage: int = 0
    special_defense_stage: int = 0
    speed_stage: int = 0

    # --- Invariantes ---------------------------------------------------

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError(
                "Pokemon requiere `name` no vacío",
                details={"name": self.name},
            )
        if not 1 <= len(self.types) <= 2:
            raise ValidationError(
                "Pokemon debe tener 1 o 2 tipos",
                details={"name": self.name, "types": [t.value for t in self.types]},
            )
        if len(set(self.types)) != len(self.types):
            raise ValidationError(
                "Tipos duplicados no permitidos",
                details={"name": self.name, "types": [t.value for t in self.types]},
            )
        if not 1 <= self.level <= 100:
            raise ValidationError(
                "Level fuera de rango [1, 100]",
                details={"name": self.name, "level": self.level},
            )
        if self.is_terastalized and self.tera_type is None:
            raise ValidationError(
                "is_terastalized=True requiere tera_type",
                details={"name": self.name},
            )
        for stage_name in _STAGE_FIELDS:
            stage = getattr(self, f"{stage_name}_stage")
            if not -_STAGE_BOUND <= stage <= _STAGE_BOUND:
                raise ValidationError(
                    f"Stage `{stage_name}` fuera de rango [-6, 6]",
                    details={"name": self.name, "stage": stage_name, "value": stage},
                )

    # --- API de dominio -----------------------------------------------

    def effective_stats(self) -> Stats:
        """Stats reales tras aplicar nivel + IVs + EVs + naturaleza.

        Importante: los *stages* competitivos NO se aplican aquí — el
        ``DamageCalculator`` los aplica por separado vía
        ``stage_multiplier`` para que el ``Stats`` resultante siga siendo
        un valor "estable" (cacheable, comparable).
        """
        return Stats(
            hp=compute_effective_stat(
                base=self.base_stats.hp,
                iv=self.ivs.hp,
                ev=self.evs.hp,
                level=self.level,
                is_hp=True,
            ),
            attack=compute_effective_stat(
                base=self.base_stats.attack,
                iv=self.ivs.attack,
                ev=self.evs.attack,
                level=self.level,
                nature_multiplier=self.nature.multiplier_for("attack"),
            ),
            defense=compute_effective_stat(
                base=self.base_stats.defense,
                iv=self.ivs.defense,
                ev=self.evs.defense,
                level=self.level,
                nature_multiplier=self.nature.multiplier_for("defense"),
            ),
            special_attack=compute_effective_stat(
                base=self.base_stats.special_attack,
                iv=self.ivs.special_attack,
                ev=self.evs.special_attack,
                level=self.level,
                nature_multiplier=self.nature.multiplier_for("special_attack"),
            ),
            special_defense=compute_effective_stat(
                base=self.base_stats.special_defense,
                iv=self.ivs.special_defense,
                ev=self.evs.special_defense,
                level=self.level,
                nature_multiplier=self.nature.multiplier_for("special_defense"),
            ),
            speed=compute_effective_stat(
                base=self.base_stats.speed,
                iv=self.ivs.speed,
                ev=self.evs.speed,
                level=self.level,
                nature_multiplier=self.nature.multiplier_for("speed"),
            ),
        )

    def stage_multiplier(self, stat: str) -> float:
        """Multiplicador derivado del stage actual del stat indicado.

        ``stat`` esperado: ``"attack" | "defense" | "special_attack"``
        ``| "special_defense" | "speed"``. Cualquier otro valor devuelve 1.0
        para no romper callsites por error de tipeo (defensivo).
        """
        if stat not in _STAGE_FIELDS:
            return 1.0
        stage_value = getattr(self, f"{stat}_stage", 0)
        return _stage_to_multiplier(stage_value)


__all__ = ["Ability", "Move", "Pokemon"]

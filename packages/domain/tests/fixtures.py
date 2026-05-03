"""Fixtures de Pokémon canónicos para tests.

Stats base tomados del Pokédex Gen IX. Los builds (level 100, 252 EVs en
attacking + speed, neutral natures salvo nota) están elegidos para que
los daños sean replicables a mano y/o en damage calc públicos.
"""

from __future__ import annotations

from domain.pokemon.entities import Ability, Move, Pokemon
from domain.pokemon.value_objects import (
    EVs,
    IVs,
    MoveCategory,
    Nature,
    Stats,
    Type,
)

# --- Habilidades ----------------------------------------------------------

ABILITY_GENERIC = Ability(name="Generic", description="Habilidad sin efectos modelados")
ABILITY_ADAPTABILITY = Ability(name="Adaptability", boosts_stab_to_2x=True)


# --- Pokémon --------------------------------------------------------------


def garchomp(
    *,
    level: int = 100,
    nature: Nature = Nature.JOLLY,
    evs: EVs | None = None,
    ivs: IVs | None = None,
) -> Pokemon:
    """Garchomp 108/130/95/80/85/102 — Dragon/Ground."""
    return Pokemon(
        name="Garchomp",
        types=(Type.DRAGON, Type.GROUND),
        base_stats=Stats(
            hp=108, attack=130, defense=95,
            special_attack=80, special_defense=85, speed=102,
        ),
        ability=ABILITY_GENERIC,
        level=level,
        nature=nature,
        evs=evs or EVs(attack=252, speed=252, hp=4),
        ivs=ivs or IVs(),
    )


def salamence(*, level: int = 100, nature: Nature = Nature.NAIVE) -> Pokemon:
    """Salamence 95/135/80/110/80/100 — Dragon/Flying."""
    return Pokemon(
        name="Salamence",
        types=(Type.DRAGON, Type.FLYING),
        base_stats=Stats(
            hp=95, attack=135, defense=80,
            special_attack=110, special_defense=80, speed=100,
        ),
        ability=ABILITY_GENERIC,
        level=level,
        nature=nature,
        evs=EVs(attack=252, speed=252, hp=4),
    )


def blissey(*, level: int = 100) -> Pokemon:
    """Blissey 255/10/10/75/135/55 — Normal puro, muralla especial."""
    return Pokemon(
        name="Blissey",
        types=(Type.NORMAL,),
        base_stats=Stats(
            hp=255, attack=10, defense=10,
            special_attack=75, special_defense=135, speed=55,
        ),
        ability=ABILITY_GENERIC,
        level=level,
        nature=Nature.CALM,
        evs=EVs(hp=252, defense=252, special_defense=4),
    )


def charizard(*, level: int = 100, nature: Nature = Nature.TIMID) -> Pokemon:
    """Charizard 78/84/78/109/85/100 — Fire/Flying."""
    return Pokemon(
        name="Charizard",
        types=(Type.FIRE, Type.FLYING),
        base_stats=Stats(
            hp=78, attack=84, defense=78,
            special_attack=109, special_defense=85, speed=100,
        ),
        ability=ABILITY_GENERIC,
        level=level,
        nature=nature,
        evs=EVs(special_attack=252, speed=252, hp=4),
    )


def venusaur(*, level: int = 100, nature: Nature = Nature.MODEST) -> Pokemon:
    """Venusaur 80/82/83/100/100/80 — Grass/Poison."""
    return Pokemon(
        name="Venusaur",
        types=(Type.GRASS, Type.POISON),
        base_stats=Stats(
            hp=80, attack=82, defense=83,
            special_attack=100, special_defense=100, speed=80,
        ),
        ability=ABILITY_GENERIC,
        level=level,
        nature=nature,
        evs=EVs(special_attack=252, hp=252, special_defense=4),
    )


def gengar(*, level: int = 100, nature: Nature = Nature.TIMID) -> Pokemon:
    """Gengar 60/65/60/130/75/110 — Ghost/Poison."""
    return Pokemon(
        name="Gengar",
        types=(Type.GHOST, Type.POISON),
        base_stats=Stats(
            hp=60, attack=65, defense=60,
            special_attack=130, special_defense=75, speed=110,
        ),
        ability=ABILITY_GENERIC,
        level=level,
        nature=nature,
        evs=EVs(special_attack=252, speed=252, hp=4),
    )


def porygon_z(
    *,
    level: int = 100,
    nature: Nature = Nature.MODEST,
    ability: Ability = ABILITY_ADAPTABILITY,
) -> Pokemon:
    """Porygon-Z 85/80/70/135/75/90 — Normal puro con Adaptability."""
    return Pokemon(
        name="Porygon-Z",
        types=(Type.NORMAL,),
        base_stats=Stats(
            hp=85, attack=80, defense=70,
            special_attack=135, special_defense=75, speed=90,
        ),
        ability=ability,
        level=level,
        nature=nature,
        evs=EVs(special_attack=252, speed=252, hp=4),
    )


# --- Movimientos ----------------------------------------------------------

EARTHQUAKE = Move(
    name="Earthquake",
    type=Type.GROUND,
    category=MoveCategory.PHYSICAL,
    power=100,
    accuracy=100,
    pp=10,
    makes_contact=False,
)

ICE_FANG = Move(
    name="Ice Fang",
    type=Type.ICE,
    category=MoveCategory.PHYSICAL,
    power=65,
    accuracy=95,
    pp=15,
    makes_contact=True,
    is_biting=True,
)

THUNDERBOLT = Move(
    name="Thunderbolt",
    type=Type.ELECTRIC,
    category=MoveCategory.SPECIAL,
    power=90,
    accuracy=100,
    pp=15,
)

FLAMETHROWER = Move(
    name="Flamethrower",
    type=Type.FIRE,
    category=MoveCategory.SPECIAL,
    power=90,
    accuracy=100,
    pp=15,
)

HYDRO_PUMP = Move(
    name="Hydro Pump",
    type=Type.WATER,
    category=MoveCategory.SPECIAL,
    power=110,
    accuracy=80,
    pp=5,
)

SHADOW_BALL = Move(
    name="Shadow Ball",
    type=Type.GHOST,
    category=MoveCategory.SPECIAL,
    power=80,
    accuracy=100,
    pp=15,
)

DRAGON_CLAW = Move(
    name="Dragon Claw",
    type=Type.DRAGON,
    category=MoveCategory.PHYSICAL,
    power=80,
    accuracy=100,
    pp=15,
    makes_contact=True,
)

TACKLE = Move(
    name="Tackle",
    type=Type.NORMAL,
    category=MoveCategory.PHYSICAL,
    power=40,
    accuracy=100,
    pp=35,
    makes_contact=True,
)


__all__ = [
    "ABILITY_ADAPTABILITY",
    "ABILITY_GENERIC",
    "DRAGON_CLAW",
    "EARTHQUAKE",
    "FLAMETHROWER",
    "HYDRO_PUMP",
    "ICE_FANG",
    "SHADOW_BALL",
    "TACKLE",
    "THUNDERBOLT",
    "blissey",
    "charizard",
    "garchomp",
    "gengar",
    "porygon_z",
    "salamence",
    "venusaur",
]

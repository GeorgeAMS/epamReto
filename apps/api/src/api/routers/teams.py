"""Router para construccion de equipos Pokemon."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamBuildRequest(BaseModel):
    anchor_pokemon: str
    format: str = "OU"
    team_size: int = 6


class TeamMember(BaseModel):
    pokemon: str
    types: list[str]
    ability: str
    item: str | None = None
    sprite: str
    base_stats: dict[str, int]
    role: str | None = None


class TypeCoverageResponse(BaseModel):
    team: list[TeamMember]
    heatmap: list[list[float]]
    weaknesses: dict[str, int]
    resistances: dict[str, int]


TYPE_CHART = {
    "normal": {"fighting": 2.0, "ghost": 0.0},
    "fire": {"water": 2.0, "ground": 2.0, "rock": 2.0, "fire": 0.5, "grass": 0.5, "ice": 0.5, "bug": 0.5, "steel": 0.5, "fairy": 0.5},
    "water": {"electric": 2.0, "grass": 2.0, "fire": 0.5, "water": 0.5, "ice": 0.5, "steel": 0.5},
    "electric": {"ground": 2.0, "electric": 0.5, "flying": 0.5, "steel": 0.5},
    "grass": {"fire": 2.0, "ice": 2.0, "poison": 2.0, "flying": 2.0, "bug": 2.0, "water": 0.5, "grass": 0.5, "electric": 0.5, "ground": 0.5},
    "ice": {"fire": 2.0, "fighting": 2.0, "rock": 2.0, "steel": 2.0, "ice": 0.5},
    "fighting": {"flying": 2.0, "psychic": 2.0, "fairy": 2.0, "bug": 0.5, "rock": 0.5, "dark": 0.5},
    "poison": {"ground": 2.0, "psychic": 2.0, "fighting": 0.5, "poison": 0.5, "bug": 0.5, "grass": 0.5, "fairy": 0.5},
    "ground": {"water": 2.0, "grass": 2.0, "ice": 2.0, "poison": 0.5, "rock": 0.5, "electric": 0.0},
    "flying": {"electric": 2.0, "ice": 2.0, "rock": 2.0, "fighting": 0.5, "bug": 0.5, "grass": 0.5, "ground": 0.0},
    "psychic": {"bug": 2.0, "ghost": 2.0, "dark": 2.0, "fighting": 0.5, "psychic": 0.5},
    "bug": {"fire": 2.0, "flying": 2.0, "rock": 2.0, "fighting": 0.5, "ground": 0.5, "grass": 0.5},
    "rock": {"water": 2.0, "grass": 2.0, "fighting": 2.0, "ground": 2.0, "steel": 2.0, "normal": 0.5, "fire": 0.5, "poison": 0.5, "flying": 0.5},
    "ghost": {"ghost": 2.0, "dark": 2.0, "poison": 0.5, "bug": 0.5, "normal": 0.0, "fighting": 0.0},
    "dragon": {"ice": 2.0, "dragon": 2.0, "fairy": 2.0, "fire": 0.5, "water": 0.5, "electric": 0.5, "grass": 0.5},
    "dark": {"fighting": 2.0, "bug": 2.0, "fairy": 2.0, "ghost": 0.5, "dark": 0.5, "psychic": 0.0},
    "steel": {"fire": 2.0, "fighting": 2.0, "ground": 2.0, "normal": 0.5, "grass": 0.5, "ice": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "rock": 0.5, "dragon": 0.5, "steel": 0.5, "fairy": 0.5, "poison": 0.0},
    "fairy": {"poison": 2.0, "steel": 2.0, "fighting": 0.5, "bug": 0.5, "dark": 0.5, "dragon": 0.0},
}

ALL_TYPES = list(TYPE_CHART.keys())


async def fetch_pokemon_data(name: str) -> TeamMember | None:
    """Obtiene datos de un Pokemon desde PokeAPI."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://pokeapi.co/api/v2/pokemon/{name.lower()}", timeout=10.0)
            if response.status_code != 200:
                return None
            data = response.json()
            return TeamMember(
                pokemon=data["name"],
                types=[t["type"]["name"] for t in data["types"]],
                ability=data["abilities"][0]["ability"]["name"] if data["abilities"] else "unknown",
                sprite=data["sprites"]["front_default"] or "",
                base_stats={
                    "hp": data["stats"][0]["base_stat"],
                    "attack": data["stats"][1]["base_stat"],
                    "defense": data["stats"][2]["base_stat"],
                    "special_attack": data["stats"][3]["base_stat"],
                    "special_defense": data["stats"][4]["base_stat"],
                    "speed": data["stats"][5]["base_stat"],
                    "total": sum(s["base_stat"] for s in data["stats"]),
                },
            )
    except Exception:
        return None


def calculate_effectiveness(defending_types: list[str], attacking_type: str) -> float:
    """Calcula efectividad de un tipo atacante contra tipos defensivos."""
    multiplier = 1.0
    for defending_type in defending_types:
        type_matchups = TYPE_CHART.get(defending_type, {})
        multiplier *= type_matchups.get(attacking_type, 1.0)
    return multiplier


def analyze_coverage(team: list[TeamMember]) -> dict[str, Any]:
    """Analiza cobertura de tipos del equipo."""
    heatmap: list[list[float]] = []
    for attacking_type in ALL_TYPES:
        row: list[float] = []
        for member in team:
            row.append(calculate_effectiveness(member.types, attacking_type))
        heatmap.append(row)

    weaknesses: dict[str, int] = defaultdict(int)
    resistances: dict[str, int] = defaultdict(int)

    for member in team:
        for attacking_type in ALL_TYPES:
            effectiveness = calculate_effectiveness(member.types, attacking_type)
            if effectiveness >= 2.0:
                weaknesses[attacking_type] += 1
            elif effectiveness <= 0.5:
                resistances[attacking_type] += 1

    return {
        "heatmap": heatmap,
        "weaknesses": dict(weaknesses),
        "resistances": dict(resistances),
    }


@router.post("/build", response_model=TypeCoverageResponse)
async def build_team(request: TeamBuildRequest) -> TypeCoverageResponse:
    """Construye un equipo basico alrededor de un anchor Pokemon."""
    anchor = await fetch_pokemon_data(request.anchor_pokemon)
    if not anchor:
        raise HTTPException(404, f"Pokemon '{request.anchor_pokemon}' not found")

    suggested_names = {
        "garchomp": ["toxapex", "ferrothorn", "landorus-therian", "tapu-koko", "heatran"],
        "dragapult": ["corviknight", "toxapex", "clefable", "tyranitar", "excadrill"],
        "pikachu": ["raichu", "jolteon", "magnezone", "rotom-wash", "zapdos"],
        "charizard": ["blastoise", "gyarados", "tyranitar", "excadrill", "rotom-wash"],
    }
    suggestions = suggested_names.get(
        request.anchor_pokemon.lower(),
        ["tyranitar", "ferrothorn", "toxapex", "landorus-therian", "corviknight"],
    )

    team_members = [anchor]
    for name in suggestions[: max(1, request.team_size - 1)]:
        member = await fetch_pokemon_data(name)
        if member:
            team_members.append(member)

    coverage = analyze_coverage(team_members)
    return TypeCoverageResponse(
        team=team_members,
        heatmap=coverage["heatmap"],
        weaknesses=coverage["weaknesses"],
        resistances=coverage["resistances"],
    )


@router.post("/coverage")
async def calculate_team_coverage(pokemon_names: list[str]) -> dict[str, Any]:
    """Calcula cobertura de tipos para una lista de Pokemon."""
    team: list[TeamMember] = []
    for name in pokemon_names:
        member = await fetch_pokemon_data(name)
        if member:
            team.append(member)

    if not team:
        raise HTTPException(400, "No valid Pokemon provided")

    coverage = analyze_coverage(team)
    return {"team": team, **coverage}


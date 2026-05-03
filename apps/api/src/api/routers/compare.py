"""Router para comparacion de Pokemon."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
import httpx
from pydantic import BaseModel

router = APIRouter(prefix="/compare", tags=["compare"])


class PokemonStats(BaseModel):
    name: str
    types: list[str]
    base_stats: dict[str, int]
    sprite: str
    ability: str


class CompareResponse(BaseModel):
    pokemon: list[PokemonStats]
    matchups: dict[str, dict[str, str]]
    winner: str | None = None


async def fetch_pokemon_for_compare(name: str) -> PokemonStats | None:
    """Obtiene datos de Pokemon para comparacion."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://pokeapi.co/api/v2/pokemon/{name.lower()}",
                timeout=10.0,
            )
            if response.status_code != 200:
                return None
            data = response.json()
            return PokemonStats(
                name=data["name"],
                types=[t["type"]["name"] for t in data["types"]],
                base_stats={
                    "hp": data["stats"][0]["base_stat"],
                    "attack": data["stats"][1]["base_stat"],
                    "defense": data["stats"][2]["base_stat"],
                    "special_attack": data["stats"][3]["base_stat"],
                    "special_defense": data["stats"][4]["base_stat"],
                    "speed": data["stats"][5]["base_stat"],
                    "total": sum(s["base_stat"] for s in data["stats"]),
                },
                sprite=data["sprites"]["front_default"] or "",
                ability=data["abilities"][0]["ability"]["name"] if data["abilities"] else "unknown",
            )
    except Exception:
        return None


def calculate_matchup(pokemon1: PokemonStats, pokemon2: PokemonStats) -> dict[str, str]:
    """Calcula matchup basico entre dos Pokemon."""
    advantages: list[str] = []
    if pokemon1.base_stats["speed"] > pokemon2.base_stats["speed"]:
        advantages.append(f"{pokemon1.name} is faster")
    elif pokemon2.base_stats["speed"] > pokemon1.base_stats["speed"]:
        advantages.append(f"{pokemon2.name} is faster")

    if pokemon1.base_stats["total"] > pokemon2.base_stats["total"]:
        advantages.append(f"{pokemon1.name} has higher BST")
    elif pokemon2.base_stats["total"] > pokemon1.base_stats["total"]:
        advantages.append(f"{pokemon2.name} has higher BST")

    type_advantages: list[str] = []
    if "water" in pokemon1.types and "fire" in pokemon2.types:
        type_advantages.append(f"{pokemon1.name} resists Fire attacks")
    if "fire" in pokemon1.types and "grass" in pokemon2.types:
        type_advantages.append(f"{pokemon1.name} is super effective against Grass")

    return {
        "stat_advantages": ", ".join(advantages) if advantages else "Even stats",
        "type_advantages": ", ".join(type_advantages) if type_advantages else "Neutral typing",
        "summary": advantages[0] if advantages else "Close matchup",
    }


@router.post("/", response_model=CompareResponse)
async def compare_pokemon(pokemon_names: list[str]) -> CompareResponse:
    """Compara de 2 a 4 Pokemon lado a lado."""
    if len(pokemon_names) < 2:
        raise HTTPException(400, "Must provide at least 2 Pokemon to compare")
    if len(pokemon_names) > 4:
        raise HTTPException(400, "Cannot compare more than 4 Pokemon at once")

    pokemon_list: list[PokemonStats] = []
    for name in pokemon_names:
        pokemon = await fetch_pokemon_for_compare(name)
        if not pokemon:
            raise HTTPException(404, f"Pokemon '{name}' not found")
        pokemon_list.append(pokemon)

    matchups: dict[str, dict[str, str]] = {}
    for i, p1 in enumerate(pokemon_list):
        for j, p2 in enumerate(pokemon_list):
            if i < j:
                key = f"{p1.name}_vs_{p2.name}"
                matchups[key] = calculate_matchup(p1, p2)

    winner = max(pokemon_list, key=lambda p: p.base_stats["total"]).name
    return CompareResponse(
        pokemon=pokemon_list,
        matchups=matchups,
        winner=winner,
    )


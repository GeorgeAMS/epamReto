from __future__ import annotations

import asyncio
import ast
import json
from pathlib import Path
from typing import Annotated, Any

import aiosqlite
import duckdb
import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from infrastructure.settings import get_settings
from shared.logging import get_logger

router = APIRouter(prefix="/pokedex", tags=["pokedex"])
log = get_logger(__name__)

_GENERATION_RANGES: list[tuple[int, int, int]] = [
    (1, 1, 151),
    (2, 152, 251),
    (3, 252, 386),
    (4, 387, 493),
    (5, 494, 649),
    (6, 650, 721),
    (7, 722, 809),
    (8, 810, 905),
    (9, 906, 1025),
]

_GEN_ID_RANGE: dict[int, tuple[int, int]] = {
    1: (1, 151),
    2: (152, 251),
    3: (252, 386),
    4: (387, 493),
    5: (494, 649),
    6: (650, 721),
    7: (722, 809),
    8: (810, 905),
    9: (906, 1025),
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _generation_from_id(pokemon_id: int) -> int:
    for generation, start, end in _GENERATION_RANGES:
        if start <= pokemon_id <= end:
            return generation
    return 1


def _duckdb_candidates() -> list[Path]:
    """Rutas donde puede estar la BD (ingesta CSV vs layout antiguo vs cwd api)."""
    root = _repo_root()
    raw = Path(get_settings().duckdb_path)
    if raw.is_absolute():
        resolved = raw
    else:
        resolved = (Path.cwd() / raw).resolve()
    return [
        root / "data" / "processed" / "pokemon.duckdb",
        root / "data" / "pokedex.duckdb",
        resolved,
        root / "apps" / "api" / "data" / "pokedex.duckdb",
    ]


def _first_existing_duckdb() -> Path | None:
    seen: set[str] = set()
    for p in _duckdb_candidates():
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        if p.exists():
            return p
    return None


def _pokeapi_db_path() -> Path:
    return _repo_root() / "data" / "pokeapi.db"


class PokemonListItem(BaseModel):
    id: int
    name: str
    types: list[str]
    sprite_url: str
    generation: int


class PokemonDetail(BaseModel):
    id: int
    name: str
    types: list[str]
    stats: dict[str, int]
    abilities: list[str]
    height: float
    weight: float
    sprite_url: str
    artwork_url: str
    generation: int
    species: str
    evolution_chain: list[str] | None


def _list_pokemon_from_duckdb(
    *,
    db_path: Path,
    limit: int,
    offset: int,
    generation: int | None,
    type_filter: str | None,
    search: str | None,
) -> list[PokemonListItem]:
    with duckdb.connect(str(db_path)) as conn:
        columns = {r[0] for r in conn.execute("DESCRIBE pokemon").fetchall()}
        type1_col = "type1" if "type1" in columns else "primary_type"
        type2_col = "type2" if "type2" in columns else "secondary_type"

        query = f"SELECT id, name, {type1_col}, {type2_col} FROM pokemon WHERE 1=1"
        params: list[Any] = []

        if type_filter:
            type_lower = type_filter.strip().lower()
            query += (
                f" AND (LOWER(COALESCE({type1_col}, '')) = ? "
                f"OR LOWER(COALESCE({type2_col}, '')) = ?)"
            )
            params.extend([type_lower, type_lower])

        if generation:
            if generation in _GEN_ID_RANGE:
                start, end = _GEN_ID_RANGE[generation]
                query += f" AND id BETWEEN {start} AND {end}"

        if search:
            query += " AND LOWER(name) LIKE ?"
            params.append(f"%{search.lower()}%")

        query += f" ORDER BY id LIMIT {limit} OFFSET {offset}"
        rows = conn.execute(query, params).fetchall()

    pokemon_list: list[PokemonListItem] = []
    for row in rows:
        row_types = [t for t in [row[2], row[3]] if t]
        pokemon_list.append(
            PokemonListItem(
                id=row[0],
                name=row[1],
                types=row_types,
                sprite_url=f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{row[0]}.png",
                generation=_generation_from_id(row[0]),
            )
        )
    return pokemon_list


async def _fetch_list_item(client: httpx.AsyncClient, base: str, pid: int) -> PokemonListItem | None:
    try:
        r = await client.get(f"{base}/pokemon/{pid}")
        r.raise_for_status()
        data = r.json()
        types = [t["type"]["name"] for t in data["types"]]
        sid = int(data["id"])
        sprite = data.get("sprites") or {}
        sprite_url = sprite.get("front_default") or (
            f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{sid}.png"
        )
        return PokemonListItem(
            id=sid,
            name=str(data["name"]),
            types=types,
            sprite_url=sprite_url,
            generation=_generation_from_id(sid),
        )
    except Exception as exc:
        log.warning("pokedex.pokeapi_list_item_failed", pokemon_id=pid, error=str(exc))
        return None


async def _list_pokemon_from_pokeapi_http(
    *,
    limit: int,
    offset: int,
    generation: int | None,
    type_filter: str | None,
    search: str | None,
) -> list[PokemonListItem]:
    """Respaldo en red cuando no hay DuckDB (misma ventana id que el SQL, sin filtros tipo/búsqueda)."""
    if type_filter or search:
        raise HTTPException(
            status_code=503,
            detail=(
                "Sin base DuckDB no se pueden aplicar filtros por tipo o búsqueda por nombre. "
                "Genera data/pokedex.duckdb con el CSV (ver README: load_kaggle_csv) o copia el .duckdb "
                "desde una máquina donde ya esté construido."
            ),
        )
    settings = get_settings()
    base = settings.pokeapi_base_url.rstrip("/")
    if generation and generation in _GEN_ID_RANGE:
        lo, hi = _GEN_ID_RANGE[generation]
        pool = list(range(lo, hi + 1))
    else:
        pool = list(range(1, 1026))
    slice_ids = pool[offset : offset + limit]
    if not slice_ids:
        return []

    sem = asyncio.Semaphore(16)

    async with httpx.AsyncClient(timeout=25.0) as client:

        async def _one(pid: int) -> PokemonListItem | None:
            async with sem:
                return await _fetch_list_item(client, base, pid)

        results = await asyncio.gather(*(_one(pid) for pid in slice_ids))
    return [x for x in results if x is not None]


async def _detail_from_pokeapi_http(pokemon_id: int) -> PokemonDetail:
    settings = get_settings()
    base = settings.pokeapi_base_url.rstrip("/")
    async with httpx.AsyncClient(timeout=25.0) as client:
        r = await client.get(f"{base}/pokemon/{pokemon_id}")
        r.raise_for_status()
        data = r.json()
    artwork = (
        (data.get("sprites") or {})
        .get("other", {})
        .get("official-artwork", {})
        .get("front_default")
    )
    if not artwork:
        artwork = (
            "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/"
            f"{data['id']}.png"
        )
    return PokemonDetail(
        id=data["id"],
        name=data["name"],
        types=[t["type"]["name"] for t in data["types"]],
        stats={s["stat"]["name"]: s["base_stat"] for s in data["stats"]},
        abilities=[a["ability"]["name"] for a in data["abilities"]],
        height=data["height"] / 10,
        weight=data["weight"] / 10,
        sprite_url=data["sprites"]["front_default"]
        or f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{data['id']}.png",
        artwork_url=artwork,
        generation=_generation_from_id(data["id"]),
        species=data["species"]["name"],
        evolution_chain=None,
    )


@router.get("/pokemon", response_model=list[PokemonListItem])
async def list_pokemon(
    limit: Annotated[int, Query(ge=1, le=1025)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    generation: Annotated[int | None, Query()] = None,
    type_filter: Annotated[
        str | None,
        Query(alias="type", description="Tipo principal o secundario"),
    ] = None,
    search: Annotated[str | None, Query()] = None,
) -> list[PokemonListItem]:
    """Lista Pokémon con filtros. Si no hay DuckDB local, usa PokéAPI (sin tipo/búsqueda)."""
    db_path = _first_existing_duckdb()
    if db_path is not None:
        try:
            return _list_pokemon_from_duckdb(
                db_path=db_path,
                limit=limit,
                offset=offset,
                generation=generation,
                type_filter=type_filter,
                search=search,
            )
        except Exception as exc:
            log.warning(
                "pokedex.duckdb_list_failed",
                path=str(db_path),
                error=str(exc),
                exc_info=True,
            )
    try:
        return await _list_pokemon_from_pokeapi_http(
            limit=limit,
            offset=offset,
            generation=generation,
            type_filter=type_filter,
            search=search,
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.error("pokedex.list_unavailable", error=str(exc), exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=(
                "No hay base DuckDB (p. ej. data/pokedex.duckdb) y PokéAPI no respondió. "
                f"Último error: {exc!s}"
            ),
        ) from exc


@router.get("/pokemon/{pokemon_id}", response_model=PokemonDetail)
async def get_pokemon(pokemon_id: int) -> PokemonDetail:
    """Detalle completo de un Pokemon."""
    pokeapi_db_path = _pokeapi_db_path()
    if pokeapi_db_path.exists():
        async with aiosqlite.connect(str(pokeapi_db_path)) as db:
            cursor = await db.execute("SELECT data FROM pokemon WHERE id = ?", (pokemon_id,))
            row = await cursor.fetchone()
            await cursor.close()

        if row:
            data = json.loads(row[0])
            artwork_url = data["sprites"]["other"]["official-artwork"]["front_default"]
            return PokemonDetail(
                id=data["id"],
                name=data["name"],
                types=[t["type"]["name"] for t in data["types"]],
                stats={s["stat"]["name"]: s["base_stat"] for s in data["stats"]},
                abilities=[a["ability"]["name"] for a in data["abilities"]],
                height=data["height"] / 10,
                weight=data["weight"] / 10,
                sprite_url=data["sprites"]["front_default"],
                artwork_url=artwork_url,
                generation=_generation_from_id(data["id"]),
                species=data["species"]["name"],
                evolution_chain=None,
            )

    duckdb_path = _first_existing_duckdb()
    if duckdb_path is not None:
        try:
            with duckdb.connect(str(duckdb_path)) as conn:
                row = conn.execute(
                    """
                    SELECT id, name, primary_type, secondary_type, hp, attack, defense, sp_atk, sp_def, speed,
                           abilities, height_m, weight_kg, generation, classfication
                    FROM pokemon
                    WHERE id = ?
                    """,
                    [pokemon_id],
                ).fetchone()

            if row:
                raw_abilities = row[10]
                if isinstance(raw_abilities, str) and raw_abilities.strip().startswith("["):
                    try:
                        parsed = ast.literal_eval(raw_abilities)
                        abilities = [str(ability) for ability in parsed]
                    except (SyntaxError, ValueError):
                        abilities = [
                            ability.strip() for ability in raw_abilities.split(",") if ability.strip()
                        ]
                else:
                    abilities = [
                        ability.strip() for ability in str(raw_abilities).split(",") if ability.strip()
                    ]
                sprite_url = (
                    f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{row[0]}.png"
                )
                artwork_url = (
                    "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/"
                    "official-artwork/"
                    f"{row[0]}.png"
                )
                return PokemonDetail(
                    id=row[0],
                    name=row[1],
                    types=[row[2], row[3]] if row[3] else [row[2]],
                    stats={
                        "hp": row[4],
                        "attack": row[5],
                        "defense": row[6],
                        "special-attack": row[7],
                        "special-defense": row[8],
                        "speed": row[9],
                    },
                    abilities=abilities,
                    height=float(row[11]) if row[11] is not None else 0.0,
                    weight=float(row[12]) if row[12] is not None else 0.0,
                    sprite_url=sprite_url,
                    artwork_url=artwork_url,
                    generation=row[13] if row[13] else _generation_from_id(row[0]),
                    species=row[14] or "unknown",
                    evolution_chain=None,
                )
        except Exception as exc:
            log.warning(
                "pokedex.duckdb_detail_failed",
                path=str(duckdb_path),
                pokemon_id=pokemon_id,
                error=str(exc),
                exc_info=True,
            )

    try:
        return await _detail_from_pokeapi_http(pokemon_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Pokemon not found") from exc
        raise HTTPException(status_code=502, detail=f"PokéAPI error: {exc!s}") from exc
    except Exception as exc:
        log.error("pokedex.detail_unavailable", pokemon_id=pokemon_id, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=(
                "No hay DuckDB ni caché SQLite (data/pokeapi.db) y no se pudo leer de PokéAPI. "
                f"Error: {exc!s}"
            ),
        ) from exc


@router.get("/types")
async def list_types() -> dict[str, list[str]]:
    """Lista de todos los tipos de Pokemon."""
    return {
        "types": [
            "normal",
            "fire",
            "water",
            "electric",
            "grass",
            "ice",
            "fighting",
            "poison",
            "ground",
            "flying",
            "psychic",
            "bug",
            "rock",
            "ghost",
            "dragon",
            "dark",
            "steel",
            "fairy",
        ]
    }


@router.get("/generations")
async def list_generations() -> dict[str, list[dict[str, Any]]]:
    """Lista de generaciones."""
    return {
        "generations": [
            {"id": 1, "name": "Gen I (Kanto)", "range": [1, 151]},
            {"id": 2, "name": "Gen II (Johto)", "range": [152, 251]},
            {"id": 3, "name": "Gen III (Hoenn)", "range": [252, 386]},
            {"id": 4, "name": "Gen IV (Sinnoh)", "range": [387, 493]},
            {"id": 5, "name": "Gen V (Unova)", "range": [494, 649]},
            {"id": 6, "name": "Gen VI (Kalos)", "range": [650, 721]},
            {"id": 7, "name": "Gen VII (Alola)", "range": [722, 809]},
            {"id": 8, "name": "Gen VIII (Galar)", "range": [810, 905]},
            {"id": 9, "name": "Gen IX (Paldea)", "range": [906, 1025]},
        ]
    }

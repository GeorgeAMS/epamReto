"""Cliente PokéAPI con cache local SQLite.

Diseño:
- ``httpx.Client`` síncrono (suficiente para hackathon; el reto no es escalar).
- Cache persistente con `diskcache` (TTL grande: los datos canon casi no cambian).
- Reintentos con backoff exponencial (`tenacity`) para huecos de red durante demo.
- Mapper a entidades de dominio (`Pokemon`, `Move`) — el resto de la API se
  expone como dicts crudos para no acoplarnos en exceso.
- CLI ``typer`` con dos comandos útiles para demo:
    - ``warmup`` → hidrata cache con los 1025 pokémon en lote.
    - ``get-pokemon <name>`` → consulta puntual (imprime resumen).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import diskcache
import httpx
import typer
from rich.console import Console
from rich.table import Table
from tenacity import retry, stop_after_attempt, wait_exponential

from domain.pokemon.entities import Ability, Move, Pokemon
from domain.pokemon.value_objects import (
    EVs,
    IVs,
    MoveCategory,
    Nature,
    Stats,
    Type,
)
from infrastructure.settings import get_settings
from shared.errors import InfrastructureError
from shared.logging import configure_logging, get_logger

log = get_logger(__name__)
console = Console()


# --- Mapeos -------------------------------------------------------------


_TYPE_BY_NAME: dict[str, Type] = {t.value: t for t in Type}
_CATEGORY_BY_NAME: dict[str, MoveCategory] = {c.value: c for c in MoveCategory}


def _to_type(name: str) -> Type:
    try:
        return _TYPE_BY_NAME[name]
    except KeyError as exc:
        raise InfrastructureError(
            "Tipo PokéAPI desconocido",
            details={"name": name},
        ) from exc


# --- Cliente ------------------------------------------------------------


class PokeAPIClient:
    """Cliente síncrono con cache disco.

    Uso recomendado dentro de la API: instanciar una vez y reusar (singleton
    en `get_client`). Cierra el cliente HTTP en shutdown si se usó cliente propio.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        cache_path: str | None = None,
        ttl_seconds: int = 60 * 60 * 24 * 30,  # 30 días
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.pokeapi_base_url).rstrip("/")
        cache_dir = Path(cache_path or settings.pokeapi_cache_path).parent
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = diskcache.Cache(str(cache_dir / "pokeapi-disk"))
        self._ttl = ttl_seconds
        self._http = httpx.Client(timeout=10.0, headers={"User-Agent": "pokedex-arcana/0.1"})

    def close(self) -> None:
        self._http.close()
        self._cache.close()

    def __enter__(self) -> PokeAPIClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # --- HTTP raw ----------------------------------------------------

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    )
    def _get_json(self, path: str) -> dict[str, Any]:
        cached = self._cache.get(path)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        url = f"{self.base_url}{path}"
        log.debug("pokeapi.fetch", url=url)
        resp = self._http.get(url)
        if resp.status_code == 404:
            raise InfrastructureError(
                f"Recurso PokéAPI no encontrado: {path}",
                details={"url": url, "status": 404},
            )
        if resp.status_code >= 400:
            raise InfrastructureError(
                f"Fallo PokéAPI ({resp.status_code})",
                details={"url": url, "status": resp.status_code, "body": resp.text[:200]},
            )

        data: dict[str, Any] = resp.json()
        self._cache.set(path, data, expire=self._ttl)
        return data

    # --- Endpoints de alto nivel -------------------------------------

    def get_pokemon_raw(self, name_or_id: str | int) -> dict[str, Any]:
        return self._get_json(f"/pokemon/{str(name_or_id).lower()}")

    def get_move_raw(self, name_or_id: str | int) -> dict[str, Any]:
        return self._get_json(f"/move/{str(name_or_id).lower()}")

    def get_ability_raw(self, name_or_id: str | int) -> dict[str, Any]:
        return self._get_json(f"/ability/{str(name_or_id).lower()}")

    def list_pokemon(self, *, limit: int = 1025) -> list[dict[str, Any]]:
        data = self._get_json(f"/pokemon?limit={limit}")
        return list(data.get("results", []))

    # --- Mappers a dominio -------------------------------------------

    def to_domain_pokemon(
        self,
        name_or_id: str | int,
        *,
        level: int = 50,
        nature: Nature = Nature.HARDY,
        evs: EVs | None = None,
        ivs: IVs | None = None,
    ) -> Pokemon:
        """Convierte el JSON de PokéAPI a una entidad ``Pokemon``."""
        raw = self.get_pokemon_raw(name_or_id)
        types = tuple(
            _to_type(t["type"]["name"])
            for t in sorted(raw["types"], key=lambda x: x["slot"])
        )
        stat_map = {s["stat"]["name"]: s["base_stat"] for s in raw["stats"]}
        base = Stats(
            hp=stat_map.get("hp", 0),
            attack=stat_map.get("attack", 0),
            defense=stat_map.get("defense", 0),
            special_attack=stat_map.get("special-attack", 0),
            special_defense=stat_map.get("special-defense", 0),
            speed=stat_map.get("speed", 0),
        )
        ability_name = raw["abilities"][0]["ability"]["name"]
        ability = Ability(name=ability_name.title())

        return Pokemon(
            name=raw["name"].title(),
            types=types,
            base_stats=base,
            ability=ability,
            level=level,
            nature=nature,
            evs=evs or EVs(),
            ivs=ivs or IVs(),
        )

    def to_domain_move(self, name_or_id: str | int) -> Move:
        raw = self.get_move_raw(name_or_id)
        category_name = raw.get("damage_class", {}).get("name", "status")
        return Move(
            name=raw["name"].replace("-", " ").title(),
            type=_to_type(raw["type"]["name"]),
            category=_CATEGORY_BY_NAME.get(category_name, MoveCategory.STATUS),
            power=raw.get("power"),
            accuracy=raw.get("accuracy"),
            pp=raw.get("pp", 0),
            priority=raw.get("priority", 0),
        )


# --- Singleton para apps -------------------------------------------------


_client: PokeAPIClient | None = None


def get_client() -> PokeAPIClient:
    """Cliente compartido por la app FastAPI."""
    global _client
    if _client is None:
        _client = PokeAPIClient()
    return _client


# --- CLI -----------------------------------------------------------------


cli = typer.Typer(help="Cliente PokéAPI con cache local")


@cli.command("warmup")
def warmup_cache(limit: int = typer.Option(1025, help="Cantidad de Pokémon a cachear")) -> None:
    """Hidrata el cache local con los primeros ``limit`` Pokémon."""
    configure_logging(level="INFO", json_logs=False)
    client = PokeAPIClient()
    try:
        listing = client.list_pokemon(limit=limit)
        for i, item in enumerate(listing, 1):
            try:
                client.get_pokemon_raw(item["name"])
            except InfrastructureError as e:
                log.warning("pokeapi.warmup.skip", name=item["name"], error=str(e))
            if i % 50 == 0:
                console.log(f"Cacheados {i}/{len(listing)}")
        console.print(f"[green]OK[/green] {len(listing)} Pokémon cacheados.")
    finally:
        client.close()


@cli.command("get-pokemon")
def get_pokemon_cmd(name: str) -> None:
    """Imprime un resumen del Pokémon ``name`` desde cache (o lo pide a la API)."""
    configure_logging(level="INFO", json_logs=False)
    with PokeAPIClient() as client:
        poke = client.to_domain_pokemon(name)
        table = Table(title=f"{poke.name} (Lv{poke.level})")
        table.add_column("Stat")
        table.add_column("Valor", justify="right")
        for label, value in [
            ("Tipos", "/".join(t.value for t in poke.types)),
            ("HP", str(poke.base_stats.hp)),
            ("Attack", str(poke.base_stats.attack)),
            ("Defense", str(poke.base_stats.defense)),
            ("Sp.Atk", str(poke.base_stats.special_attack)),
            ("Sp.Def", str(poke.base_stats.special_defense)),
            ("Speed", str(poke.base_stats.speed)),
            ("BST", str(poke.base_stats.total)),
            ("Ability", poke.ability.name),
        ]:
            table.add_row(label, value)
        console.print(table)


if __name__ == "__main__":
    cli()

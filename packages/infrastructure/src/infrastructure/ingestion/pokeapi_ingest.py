"""Ingesta masiva: descarga 1025 Pokémon a la cache local.

Reusa ``PokeAPIClient.get_pokemon_raw`` (que ya cachea en disco con TTL 30d).
La idea es **calentar la cache antes de la demo** para que el ``stats_agent``
nunca pegue a la red en vivo.

Uso CLI::

    uv run python -m infrastructure.ingestion.pokeapi_ingest run --limit 1025

También expone ``warmup_cache(limit, on_progress)`` para que la API o un
script lo invoquen programáticamente.
"""

from __future__ import annotations

from collections.abc import Callable

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from infrastructure.pokeapi_client import PokeAPIClient
from shared.errors import InfrastructureError
from shared.logging import configure_logging, get_logger

log = get_logger(__name__)
console = Console()

ProgressCallback = Callable[[int, int, str], None]
"""Firma: ``(current_index, total, last_pokemon_name)``."""


def warmup_cache(
    *,
    limit: int = 1025,
    client: PokeAPIClient | None = None,
    on_progress: ProgressCallback | None = None,
) -> dict[str, int]:
    """Itera sobre los primeros ``limit`` Pokémon y los cachea localmente.

    Args:
        limit: Cantidad máxima a cachear (Gen IX llega a 1025).
        client: Cliente reutilizable (si ``None`` crea uno y lo cierra).
        on_progress: Callback opcional para barra de progreso.

    Returns:
        ``{"requested": N, "cached": M, "failed": K}``.
    """
    own_client = client is None
    real_client = client or PokeAPIClient()
    listing = real_client.list_pokemon(limit=limit)

    cached = 0
    failed = 0
    try:
        for i, item in enumerate(listing, 1):
            name = str(item.get("name", "?"))
            try:
                real_client.get_pokemon_raw(name)
                cached += 1
            except InfrastructureError as exc:
                failed += 1
                log.warning("pokeapi_ingest.skip", name=name, error=str(exc))
            if on_progress is not None:
                on_progress(i, len(listing), name)
    finally:
        if own_client:
            real_client.close()

    log.info(
        "pokeapi_ingest.done",
        requested=len(listing),
        cached=cached,
        failed=failed,
    )
    return {"requested": len(listing), "cached": cached, "failed": failed}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


cli = typer.Typer(help="Warmup masivo de la cache PokéAPI.")


@cli.command("run")
def run_ingest(
    limit: int = typer.Option(1025, help="Cantidad máxima de Pokémon a cachear"),
    quiet: bool = typer.Option(False, help="No mostrar barra de progreso"),
) -> None:
    """Descarga los primeros ``limit`` Pokémon a la cache local."""
    configure_logging(level="INFO", json_logs=False)

    if quiet:
        result = warmup_cache(limit=limit)
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task_id = progress.add_task("Cacheando PokéAPI...", total=limit)

            def _on_progress(i: int, total: int, name: str) -> None:
                progress.update(task_id, completed=i, description=f"[{i}/{total}] {name}")

            result = warmup_cache(limit=limit, on_progress=_on_progress)

    console.print(
        f"[green]OK[/green] Pedidos {result['requested']}, "
        f"cacheados {result['cached']}, fallidos {result['failed']}."
    )


if __name__ == "__main__":
    cli()


__all__ = ["ProgressCallback", "warmup_cache"]

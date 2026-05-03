"""Scraper offline de Bulbapedia.

Importante: NO se ejecuta durante la demo. La idea es:
1. Día 1: dejamos el contrato y un stub que avisa.
2. Día 3: corremos ``scrape`` una sola vez sobre una lista curada de páginas
   (≤ 200), guardamos en `data/raw/bulbapedia/*.html` y luego hacemos
   chunking + embeddings → Qdrant con el pipeline de Día 3.

Respetamos `robots.txt` y limitamos rate (1 req/s) por buena ciudadanía.
"""

from __future__ import annotations

import time
from pathlib import Path

import httpx
import typer
from rich.console import Console

from shared.errors import InfrastructureError
from shared.logging import configure_logging, get_logger

log = get_logger(__name__)
console = Console()

cli = typer.Typer(help="Scraper offline de Bulbapedia (uso pre-demo)")

BASE_URL = "https://bulbapedia.bulbagarden.net/wiki/"


def _repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[5]


def run_scrape(
    pages_file: Path,
    out_dir: Path,
    *,
    rate_limit_seconds: float = 1.0,
) -> tuple[int, int]:
    """Descarga HTML por slug (path tras ``/wiki/``). Devuelve ``(ok, total_slugs)``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_lines = pages_file.read_text(encoding="utf-8").splitlines()
    slugs = [
        line.strip()
        for line in raw_lines
        if line.strip() and not line.strip().startswith("#")
    ]
    if not slugs:
        raise InfrastructureError("pages_file vacío", details={"file": str(pages_file)})

    headers = {
        "User-Agent": (
            "PokedexArcanaScraper/0.1 (educational; respectful rate limit; +https://github.com/GeorgeAMS/epamReto)"
        ),
        "Accept": "text/html",
    }
    ok = 0
    with httpx.Client(timeout=25.0, headers=headers, follow_redirects=True) as client:
        for i, slug in enumerate(slugs, 1):
            url = f"{BASE_URL}{slug}"
            log.info("bulbapedia.fetch", slug=slug, url=url)
            try:
                resp = client.get(url)
                resp.raise_for_status()
            except Exception as e:
                log.warning("bulbapedia.fail", slug=slug, error=str(e))
                continue

            safe_name = slug.replace("/", "_")
            (out_dir / f"{safe_name}.html").write_text(resp.text, encoding="utf-8")
            ok += 1
            console.log(f"[{i}/{len(slugs)}] {slug} -> {len(resp.text)} bytes")
            time.sleep(rate_limit_seconds)
    return ok, len(slugs)


@cli.command("scrape")
def scrape(
    pages_file: Path = typer.Option(
        ..., exists=True, dir_okay=False, help="Fichero con un slug por línea"
    ),
    out_dir: Path = typer.Option(Path("data/raw/bulbapedia"), help="Directorio de salida"),
    rate_limit_seconds: float = typer.Option(1.0, help="Tiempo de espera entre requests"),
) -> None:
    configure_logging(level="INFO", json_logs=False)
    ok, total = run_scrape(pages_file, out_dir, rate_limit_seconds=rate_limit_seconds)
    console.print(f"Listo: {ok}/{total} páginas guardadas en {out_dir}")


@cli.command("anime-manga")
def scrape_anime_manga(
    out_dir: Path = typer.Option(
        Path("data/raw/bulbapedia_anime_manga"),
        help="Directorio donde guardar los HTML",
    ),
    rate_limit_seconds: float = typer.Option(1.2, help="Espera entre requests (s)"),
) -> None:
    """Lista curada Bulbapedia: anime + manga + personajes clave (ver ``data/raw/bulbapedia_anime_manga_pages.txt``)."""
    configure_logging(level="INFO", json_logs=False)
    pages = _repo_root_from_here() / "data" / "raw" / "bulbapedia_anime_manga_pages.txt"
    if not pages.exists():
        raise typer.BadParameter(f"No existe {pages}")
    ok, total = run_scrape(pages, out_dir, rate_limit_seconds=rate_limit_seconds)
    console.print(f"Anime/manga: {ok}/{total} archivos en {out_dir}")
    console.print(
        "Siguiente paso (Qdrant, sin borrar species): "
        f"uv run python packages/infrastructure/ingestion/bulbapedia_ingest.py "
        f"--from-disk --no-recreate --html-dir {out_dir} --lore-topic anime_manga"
    )


if __name__ == "__main__":
    cli()

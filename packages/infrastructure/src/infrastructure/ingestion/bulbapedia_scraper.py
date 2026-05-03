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


@cli.command("scrape")
def scrape(
    pages_file: Path = typer.Option(
        ..., exists=True, dir_okay=False, help="Fichero con un slug por línea"
    ),
    out_dir: Path = typer.Option(Path("data/raw/bulbapedia"), help="Directorio de salida"),
    rate_limit_seconds: float = typer.Option(1.0, help="Tiempo de espera entre requests"),
) -> None:
    configure_logging(level="INFO", json_logs=False)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_lines = pages_file.read_text(encoding="utf-8").splitlines()
    slugs = [line.strip() for line in raw_lines if line.strip()]
    if not slugs:
        raise InfrastructureError("pages_file vacío", details={"file": str(pages_file)})

    headers = {
        "User-Agent": (
            "PokedexArcanaScraper/0.1 (hackathon project; contact: jorge@pokearca.local)"
        ),
        "Accept": "text/html",
    }

    with httpx.Client(timeout=15.0, headers=headers) as client:
        for i, slug in enumerate(slugs, 1):
            url = f"{BASE_URL}{slug}"
            log.info("bulbapedia.fetch", slug=slug, url=url)
            try:
                resp = client.get(url)
                resp.raise_for_status()
            except Exception as e:
                log.warning("bulbapedia.fail", slug=slug, error=str(e))
                continue

            (out_dir / f"{slug}.html").write_text(resp.text, encoding="utf-8")
            console.log(f"[{i}/{len(slugs)}] {slug} -> {len(resp.text)} bytes")
            time.sleep(rate_limit_seconds)


if __name__ == "__main__":
    cli()

from __future__ import annotations

import argparse
import json
import re
import time
import uuid
from pathlib import Path
from urllib.parse import unquote

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from structlog import get_logger

from infrastructure.embeddings import get_embedder
from infrastructure.settings import get_settings

logger = get_logger()

_CANONICAL_RE = re.compile(
    r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def _pokemon_names(limit: int) -> list[str]:
    """Lista de nombres de especies desde PokéAPI.

    ``limit`` alto incluye todas las entradas actuales (~1300+).
    Si ``limit <= 0``, se pide un tope amplio para cubrir el catálogo completo.
    """
    api_limit = 10000 if limit <= 0 else max(limit * 3, 1200)
    resp = httpx.get(
        f"https://pokeapi.co/api/v2/pokemon?limit={api_limit}",
        timeout=60,
    )
    resp.raise_for_status()
    return [x["name"] for x in resp.json().get("results", [])]


def _canonical_url(html: str) -> str | None:
    m = _CANONICAL_RE.search(html)
    return m.group(1).strip() if m else None


def _wiki_url_from_filename(stem: str) -> str:
    return f"https://bulbapedia.bulbagarden.net/wiki/{stem}"


def _stable_point_id(url: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, url))


def _ensure_lore_collection(client: QdrantClient, dim: int, *, recreate: bool) -> None:
    names = {c.name for c in client.get_collections().collections}
    if recreate and "pokedex_lore" in names:
        client.delete_collection(collection_name="pokedex_lore")
        names.discard("pokedex_lore")
    if "pokedex_lore" not in names:
        client.create_collection(
            collection_name="pokedex_lore",
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


def _write_report(payload: dict[str, object]) -> None:
    Path("data/raw/bulbapedia_ingest_report.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def run_from_disk(
    *,
    out_dir: Path | None = None,
    recreate: bool = True,
    batch_size: int = 20,
) -> tuple[int, int]:
    """Embebe todos los ``*.html`` de ``data/raw/bulbapedia`` y los sube a Qdrant."""
    settings = get_settings()
    root = out_dir or Path("data/raw/bulbapedia")
    if not root.is_dir():
        raise FileNotFoundError(f"No existe el directorio de HTML: {root}")

    client = QdrantClient(url=settings.qdrant_url)
    embedder = get_embedder()
    _ensure_lore_collection(client, settings.embedding_dim, recreate=recreate)

    files = sorted(root.glob("*.html"))
    pending_paths: list[Path] = []
    pending_urls: list[str] = []
    pending_titles: list[str] = []
    pending_pokemon: list[str] = []
    pending_texts: list[str] = []
    ok = 0

    def _flush_pending() -> None:
        nonlocal ok
        if not pending_texts:
            return
        vectors = embedder.embed_batch(pending_texts)
        points = [
            PointStruct(
                id=_stable_point_id(url),
                vector=vec,
                payload={
                    "title": title,
                    "text": text[:2000],
                    "url": url,
                    "source": "bulbapedia",
                    "pokemon": pokemon_guess,
                    "file": path.name,
                },
            )
            for path, url, title, pokemon_guess, text, vec in zip(
                pending_paths,
                pending_urls,
                pending_titles,
                pending_pokemon,
                pending_texts,
                vectors,
                strict=True,
            )
        ]
        client.upsert(collection_name="pokedex_lore", points=points)
        pending_paths.clear()
        pending_urls.clear()
        pending_titles.clear()
        pending_pokemon.clear()
        pending_texts.clear()

    for path in files:
        try:
            html = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("bulbapedia.disk_read_error", path=str(path), error=str(exc))
            continue
        if not html.strip():
            continue
        url = _canonical_url(html) or _wiki_url_from_filename(path.stem)
        stem_decoded = unquote(path.stem)
        title = f"Bulbapedia {stem_decoded.replace('_', ' ')}"
        text = html[:4000]
        pokemon_guess = stem_decoded.split("_(")[0].replace("_", " ").lower()
        pending_paths.append(path)
        pending_urls.append(url)
        pending_titles.append(title)
        pending_pokemon.append(pokemon_guess)
        pending_texts.append(text)
        ok += 1
        print(f"[disk {ok}/{len(files)}] {path.name}")
        if len(pending_texts) >= batch_size:
            _flush_pending()
    _flush_pending()

    count = client.count(collection_name="pokedex_lore").count
    logger.info(
        "bulbapedia.ingest.disk_done",
        files=len(files),
        ok=ok,
        lore_count=count,
        recreate=recreate,
    )
    _write_report(
        {
            "mode": "from_disk",
            "files_total": len(files),
            "ok": ok,
            "lore_count": count,
            "recreate": recreate,
        }
    )
    return ok, int(count)


def run(limit: int, *, recreate: bool = False) -> tuple[int, int]:
    """Descarga artículos desde Bulbapedia (orden PokéAPI) y los indexa."""
    settings = get_settings()
    out_dir = Path("data/raw/bulbapedia")
    out_dir.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(url=settings.qdrant_url)
    embedder = get_embedder()

    names = _pokemon_names(limit)
    _ensure_lore_collection(client, settings.embedding_dim, recreate=recreate)
    base = "https://bulbapedia.bulbagarden.net/wiki/"
    ok = 0
    points: list[PointStruct] = []
    for name in names:
        if limit > 0 and ok >= limit:
            break
        slug = f"{name.capitalize()}_(Pok%C3%A9mon)"
        url = f"{base}{slug}"
        try:
            r = httpx.get(url, timeout=20)
            r.raise_for_status()
            html = r.text
            (out_dir / f"{slug}.html").write_text(html, encoding="utf-8")
            text = html[:4000]
            vec = embedder.embed(text)
            points.append(
                PointStruct(
                    id=_stable_point_id(url),
                    vector=vec,
                    payload={
                        "title": f"Bulbapedia {name}",
                        "text": text[:2000],
                        "url": url,
                        "source": "bulbapedia",
                        "pokemon": name,
                    },
                )
            )
            ok += 1
            label = f"{ok}/{limit}" if limit > 0 else str(ok)
            print(f"[{label}] {name}")
            if len(points) >= 20:
                client.upsert(collection_name="pokedex_lore", points=points)
                points = []
            time.sleep(0.5)
        except Exception as exc:
            logger.warning("bulbapedia.ingest_error", pokemon=name, error=str(exc))
    if points:
        client.upsert(collection_name="pokedex_lore", points=points)

    count = client.count(collection_name="pokedex_lore").count
    logger.info("bulbapedia.ingest.done", ok=ok, requested=limit, lore_count=count)
    _write_report(
        {
            "mode": "fetch",
            "ok": ok,
            "requested": limit,
            "lore_count": count,
            "recreate": recreate,
        }
    )
    return ok, int(count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingesta Bulbapedia a Qdrant (coleccion pokedex_lore).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Máximo de artículos descargados por PokéAPI. 0 = todos los Pokémon listados.",
    )
    parser.add_argument(
        "--from-disk",
        action="store_true",
        help="Indexar todos los *.html en data/raw/bulbapedia (sin red salvo embeddings).",
    )
    parser.add_argument(
        "--no-recreate",
        action="store_true",
        help="No borrar la colección antes (por defecto --from-disk sí recrea para evitar puntos viejos).",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Borrar pokedex_lore antes del ingest por fetch (por defecto fetch no borra).",
    )
    args = parser.parse_args()
    if args.from_disk:
        recreate_default = not args.no_recreate
        run_from_disk(recreate=recreate_default)
    else:
        run(args.limit, recreate=args.recreate)

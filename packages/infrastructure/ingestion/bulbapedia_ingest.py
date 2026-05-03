from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from structlog import get_logger

logger = get_logger()


def _embed_ollama(text: str, *, base_url: str = "http://localhost:11434") -> list[float]:
    resp = httpx.post(
        f"{base_url}/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    return list(resp.json()["embedding"])


def _pokemon_names(limit: int) -> list[str]:
    resp = httpx.get(f"https://pokeapi.co/api/v2/pokemon?limit={limit}", timeout=30)
    resp.raise_for_status()
    return [x["name"] for x in resp.json().get("results", [])]


def run(limit: int) -> tuple[int, int]:
    out_dir = Path("data/raw/bulbapedia")
    out_dir.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(url="http://localhost:6333")

    names = _pokemon_names(max(limit * 3, 1200))
    collections = {c.name for c in client.get_collections().collections}
    if "pokedex_lore" not in collections:
        client.create_collection(
            collection_name="pokedex_lore",
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
    base = "https://bulbapedia.bulbagarden.net/wiki/"
    ok = 0
    points: list[PointStruct] = []
    for i, name in enumerate(names, start=1):
        if ok >= limit:
            break
        slug = f"{name.capitalize()}_(Pok%C3%A9mon)"
        url = f"{base}{slug}"
        try:
            r = httpx.get(url, timeout=20)
            r.raise_for_status()
            html = r.text
            (out_dir / f"{slug}.html").write_text(html, encoding="utf-8")
            text = html[:4000]
            vec = _embed_ollama(text)
            points.append(
                PointStruct(
                    id=100000 + i,
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
            print(f"[{ok}/{limit}] {name}")
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
    Path("data/raw/bulbapedia_ingest_report.json").write_text(
        json.dumps({"ok": ok, "requested": limit, "lore_count": count}, indent=2),
        encoding="utf-8",
    )
    return ok, int(count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()
    run(args.limit)

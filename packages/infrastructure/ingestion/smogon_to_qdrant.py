from __future__ import annotations

import json
import time
from pathlib import Path

import requests
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from structlog import get_logger

logger = get_logger()

OU_TOP_100 = [
    "dragapult", "landorus-therian", "garchomp", "heatran", "ferrothorn",
    "toxapex", "corviknight", "clefable", "slowbro", "rillaboom",
    "zapdos", "tornadus-therian", "kartana", "tapu-lele", "magnezone",
    "volcarona", "scizor", "tyranitar", "excadrill", "weavile",
    "gengar", "dragonite", "melmetal", "azumarill", "gyarados",
    "rotom-wash", "jirachi", "mew", "celesteela", "tapu-fini",
    "alakazam", "blissey", "skarmory", "hippowdon", "pelipper",
    "ninetales-alola", "hydreigon", "mimikyu", "aegislash", "bisharp",
    "mandibuzz", "amoonguss", "chansey", "ditto", "gastrodon",
    "gliscor", "latios", "mamoswine", "reuniclus", "serperior",
    "blaziken", "charizard", "venusaur", "blastoise", "snorlax",
    "umbreon", "espeon", "lucario", "metagross", "salamence",
    "swampert", "breloom", "milotic", "absol", "aggron",
    "slaking", "flygon", "armaldo", "cradily", "claydol",
    "dusclops", "banette", "tropius", "chimecho", "wynaut",
    "snorunt", "sealeo", "walrein", "clamperl", "relicanth",
    "luvdisc", "bagon", "beldum", "metang", "regirock",
    "regice", "registeel", "latias", "kyogre", "groudon",
    "rayquaza", "jirachi", "deoxys", "torterra", "infernape",
    "empoleon", "staraptor", "luxray", "roserade", "rampardos",
]

def _embed_ollama(text: str, *, base_url: str = "http://localhost:11434") -> list[float]:
    resp = requests.post(
        f"{base_url}/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    return list(resp.json()["embedding"])


def load_smogon_to_qdrant() -> int:
    """Carga análisis Smogon a `pokedex_strategy` con embeddings Ollama."""
    client = QdrantClient(url="http://localhost:6333")

    smogon_file = Path("data/raw/smogon/smogon_ou_full.json")
    raw_analyses = json.loads(smogon_file.read_text(encoding="utf-8"))
    by_name = {a["pokemon"]: a for a in raw_analyses if "pokemon" in a}
    analyses = [by_name[name] for name in OU_TOP_100 if name in by_name]
    logger.info(
        "smogon.qdrant.load_start",
        total=len(analyses),
        expected=len(OU_TOP_100),
        unique_loaded=len(raw_analyses),
    )

    points: list[PointStruct] = []
    uploaded = 0
    for i, analysis in enumerate(analyses, start=1):
        text = (
            f"Pokemon: {analysis['pokemon']}\n"
            f"Tier: {analysis['tier']}\n\n"
            f"{analysis['content']}"
        )
        logger.info("smogon.embedding", index=i, total=len(analyses), pokemon=analysis["pokemon"])
        embedding = _embed_ollama(text)

        points.append(
            PointStruct(
                id=i,
                vector=embedding,
                payload={
                    "title": f"Smogon {analysis['pokemon']}",
                    "pokemon": analysis["pokemon"],
                    "tier": analysis["tier"],
                    "gen": analysis.get("gen", "sv"),
                    "text": analysis["content"][:2000],
                    "url": analysis["url"],
                    "source": "smogon",
                },
            )
        )
        if len(points) >= 10:
            client.upsert(collection_name="pokedex_strategy", points=points)
            uploaded += len(points)
            logger.info("smogon.qdrant.batch_uploaded", batch=len(points), uploaded=uploaded)
            points = []
            time.sleep(1)

    if points:
        client.upsert(collection_name="pokedex_strategy", points=points)
        uploaded += len(points)

    count = client.count(collection_name="pokedex_strategy").count
    logger.info("smogon.qdrant.done", uploaded=uploaded, total_in_collection=count)
    return int(count)


if __name__ == "__main__":
    load_smogon_to_qdrant()

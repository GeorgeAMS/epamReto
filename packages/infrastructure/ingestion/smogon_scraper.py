from __future__ import annotations

import json
import time
import argparse
from pathlib import Path

import requests
from bs4 import BeautifulSoup
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


def scrape_smogon_analysis(pokemon_name: str, gen: str = "sv") -> dict | None:
    """Scrape básico de análisis Smogon."""
    url = f"https://www.smogon.com/dex/{gen}/pokemon/{pokemon_name}/"
    try:
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        content_parts: list[str] = []
        overview = soup.find("div", class_="OverviewPage")
        if overview:
            content_parts.append(f"OVERVIEW: {overview.get_text(' ', strip=True)[:2000]}")

        strategies = soup.find_all("div", class_="StrategyPage")
        for strat in strategies[:3]:
            content_parts.append(f"STRATEGY: {strat.get_text(' ', strip=True)[:1500]}")

        # Fallback robusto: si Smogon cambia clases o renderiza distinto,
        # usamos texto plano del body para no perder el documento.
        if not content_parts and soup.body is not None:
            body_text = soup.body.get_text(" ", strip=True)
            content_parts.append(f"PAGE_TEXT: {body_text[:3500]}")

        full_content = "\n\n".join(content_parts).strip()
        if not full_content:
            return None
        return {
            "pokemon": pokemon_name,
            "tier": "OU",
            "gen": gen,
            "url": url,
            "content": full_content,
            "timestamp": time.time(),
        }
    except Exception as exc:
        logger.warning("smogon.scrape_error", pokemon=pokemon_name, error=str(exc))
        return None


def main(start: int = 1, end: int | None = None) -> list[dict]:
    output_dir = Path("data/raw/smogon")
    output_dir.mkdir(parents=True, exist_ok=True)

    end_idx = end or len(OU_TOP_100)
    selected = OU_TOP_100[start - 1 : end_idx]
    results: list[dict] = []
    failed: list[str] = []

    for local_i, pokemon in enumerate(selected, start=1):
        i = start + local_i - 1
        logger.info("smogon.scraping", index=i, total=len(OU_TOP_100), pokemon=pokemon)
        data = scrape_smogon_analysis(pokemon)
        if data:
            results.append(data)
            (output_dir / f"{pokemon}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        else:
            failed.append(pokemon)
        time.sleep(1.0)

    merged: dict[str, dict] = {}
    consolidated = output_dir / "smogon_ou_full.json"
    if consolidated.exists():
        for item in json.loads(consolidated.read_text(encoding="utf-8")):
            merged[str(item.get("pokemon", ""))] = item
    for item in results:
        merged[str(item["pokemon"])] = item

    final_results = list(merged.values())
    consolidated.write_text(
        json.dumps(final_results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("smogon.done", ok=len(results), total=len(selected), failed=len(failed))
    logger.info("smogon.consolidated_total", total=len(final_results))
    if failed:
        logger.warning("smogon.failed_list", failed=failed)
    return final_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()
    main(start=args.start, end=args.end)

"""Run killer Query 3 once via Orchestrator (no HTTP). Loads .env from repo root."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from agents.orchestrator import Orchestrator  # noqa: E402


def main() -> None:
    q = (
        "Build me a competitive OU team covering Dragapults weaknesses. "
        "Which 5 teammates do you recommend and why?"
    )
    orch = Orchestrator()
    resp = orch.handle(q)
    out = {
        "agent": resp.agent,
        "content": resp.content,
        "confidence": resp.confidence,
        "sources_count": len(resp.sources),
        "data": resp.data,
    }
    path = ROOT / "query3_production.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", path)
    print("--- content (first 2500 chars) ---")
    print(resp.content[:2500])


if __name__ == "__main__":
    sys.exit(main())

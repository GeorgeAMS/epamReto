import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for candidate in (
    ROOT,
    ROOT / "packages" / "infrastructure" / "src",
    ROOT / "packages" / "agents" / "src",
    ROOT / "packages" / "shared" / "src",
    ROOT / "packages" / "domain" / "src",
):
    p = str(candidate)
    if p not in sys.path:
        sys.path.insert(0, p)

from agents.synthesizer import Synthesizer  # noqa: E402
from infrastructure.llm_client import LLMClient  # noqa: E402

print("Testing Synthesizer standalone...")

try:
    llm = LLMClient()
    synth = Synthesizer(llm=llm)
    print("OK Synthesizer creado")
except Exception as e:
    print(f"ERROR: {e}")
    raise SystemExit(1)

state = {
    "query": "que sabes de pikachu",
    "intent": "stats",
    "entities": {"pokemon": "pikachu"},
    "stats_response": json.dumps(
        {
            "name": "pikachu",
            "types": ["electric"],
            "base_stats": {"hp": 35},
            "ability": "static",
        }
    ),
}

try:
    result = synth.synthesize(state)
    text = str(result.get("final_response", "N/A"))
    print("OK Sintesis completada")
    print(f"  Respuesta: {text[:200]}")
except Exception as e:
    print(f"ERROR en sintesis: {e}")
    import traceback

    traceback.print_exc()

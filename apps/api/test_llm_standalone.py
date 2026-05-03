import os
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

from infrastructure.llm_client import (  # noqa: E402
    LLMClient,
    LLMOptions,
    LLMRole,
)

print("Testing LLMClient standalone...")

api_key = os.getenv("GROQ_API_KEY")
print(f"GROQ_API_KEY presente: {bool(api_key)}")
print(f"GROQ_API_KEY (primeros 10 chars): {api_key[:10] if api_key else 'N/A'}")

try:
    client = LLMClient()
    print("OK LLMClient creado")
except Exception as e:
    print(f"ERROR creando LLMClient: {e}")
    raise SystemExit(1)

try:
    prompt = "Di solo 'hola' en español"
    response = client.complete(
        prompt,
        role=LLMRole.BRAIN,
        options=LLMOptions(max_tokens=10, temperature=0.3),
    )
    print(f"OK LLM respondio: {response.text}")
except Exception as e:
    print(f"ERROR llamando LLM: {e}")
    import traceback

    traceback.print_exc()

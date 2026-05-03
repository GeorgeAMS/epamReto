"""Evaluación RAGAS (faithfulness, answer_relevancy, context_precision) sobre el dataset.

RAGAS 0.2.x espera columnas ``user_input``, ``response``, ``retrieved_contexts``.

Requisitos:
- ``GROQ_API_KEY`` para el LLM evaluador.
- Ollama levantado en ``OLLAMA_BASE_URL`` para embeddings (`nomic-embed-text`).

Sin configuración, el script termina con código 0 e imprime instrucciones (útil en CI que
solo corre correctness). Forzar fallo con ``--require-openai``.

Respuestas modelo:
- Por defecto usa ``ground_truth`` como ``response`` (smoke test del pipeline RAGAS).
- ``--live-orchestrator`` llama a ``Orchestrator`` por fila (lento; requiere APIs si no offline).

Uso::

    uv sync --extra dev --extra eval
    uv run python eval/run_ragas.py
    uv run python eval/run_ragas.py --live-orchestrator
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from datasets import Dataset  # noqa: E402
from langchain_groq import ChatGroq  # noqa: E402
from langchain_ollama import OllamaEmbeddings  # noqa: E402
from ragas import evaluate  # noqa: E402
from ragas.metrics import (  # noqa: E402
    LLMContextPrecisionWithoutReference,
    answer_relevancy,
    faithfulness,
)

from agents.orchestrator import Orchestrator  # noqa: E402


def _load_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("dataset must be a JSON array")
    return data


def _build_hf_dataset(
    rows: list[dict[str, Any]], *, live: bool
) -> Dataset:
    user_inputs: list[str] = []
    responses: list[str] = []
    contexts: list[list[str]] = []
    orch = Orchestrator() if live else None
    for row in rows:
        q = row["question"]
        ctxs = list(row["contexts"])
        if live:
            assert orch is not None
            resp = orch.handle(q)
            responses.append(resp.content)
        else:
            responses.append(str(row["ground_truth"]))
        user_inputs.append(q)
        contexts.append(ctxs)
    return Dataset.from_dict(
        {
            "user_input": user_inputs,
            "response": responses,
            "retrieved_contexts": contexts,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="RAGAS runner for eval/dataset.json")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=_REPO_ROOT / "eval" / "dataset.json",
    )
    parser.add_argument(
        "--live-orchestrator",
        action="store_true",
        help="Use Orchestrator.handle per row as response (slow).",
    )
    parser.add_argument(
        "--require-openai",
        action="store_true",
        help="Exit 1 if Groq/Ollama config is missing (default: skip quietly).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Evaluate only first N rows (0 = all rows).",
    )
    args = parser.parse_args()

    has_groq = bool(os.environ.get("GROQ_API_KEY"))
    has_ollama = bool(os.environ.get("OLLAMA_BASE_URL"))
    if not (has_groq and has_ollama):
        msg = (
            "Missing GROQ_API_KEY or OLLAMA_BASE_URL -- skipping RAGAS.\n"
            "Set both vars and ensure Ollama model `nomic-embed-text` is pulled."
        )
        if args.require_openai:
            print(msg, file=sys.stderr)
            raise SystemExit(1)
        print(msg)
        raise SystemExit(0)

    rows = _load_rows(args.dataset)
    if args.limit > 0:
        rows = rows[: args.limit]
    ds = _build_hf_dataset(rows, live=args.live_orchestrator)
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url=os.environ["OLLAMA_BASE_URL"],
    )
    metrics = [
        faithfulness,
        answer_relevancy,
        LLMContextPrecisionWithoutReference(),
    ]
    result = evaluate(
        ds,
        metrics=metrics,
        llm=llm,
        embeddings=embeddings,
    )
    print(result)


if __name__ == "__main__":
    main()

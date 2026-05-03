"""Pruebas de correctness deterministas sobre `eval/dataset.json`.

- ``damage_calculator``: compara con ``DamageCalculator`` (sin LLM).
- ``orchestrator``: ``Orchestrator.handle`` + ``CalculatorRequest``. Requiere LLM
  real (``GROQ_API_KEY``): en modo offline el sintetizador devuelve un stub
  y estas pruebas se omiten.

Uso::

    uv run python eval/run_correctness.py
    uv run python eval/run_correctness.py --dataset eval/dataset.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agents.calculator_agent import CalculatorRequest
from agents.orchestrator import Orchestrator
from domain.pokemon.services import DamageCalculator
from infrastructure.llm_client import LLMClient

from eval._fixtures_registry import FIXTURES


def _load_dataset(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("dataset must be a JSON array")
    return raw


def _run_damage_calculator(check: dict[str, Any]) -> None:
    fixture_name = check["fixture"]
    if fixture_name not in FIXTURES:
        raise KeyError(f"Unknown fixture: {fixture_name}")
    bf = FIXTURES[fixture_name]
    result = DamageCalculator.calculate(
        attacker=bf.attacker,
        defender=bf.defender,
        move=bf.move,
        conditions=bf.conditions,
    )
    low, high = DamageCalculator.damage_range(
        attacker=bf.attacker,
        defender=bf.defender,
        move=bf.move,
        conditions=bf.conditions,
    )
    expect_d = int(check["expect_damage"])
    exp_low, exp_high = int(check["expect_range"][0]), int(check["expect_range"][1])
    if result.damage != expect_d:
        raise AssertionError(
            f"expected damage {expect_d} got {result.damage} for {fixture_name}"
        )
    if (low, high) != (exp_low, exp_high):
        raise AssertionError(
            f"expected range {(exp_low, exp_high)} got {(low, high)} for {fixture_name}"
        )


def _run_orchestrator(
    item: dict[str, Any],
    check: dict[str, Any],
    *,
    orch: Orchestrator,
    force_skip: bool,
) -> str:
    """Devuelve ``\"ok\"`` o ``\"skipped_offline\"``."""
    if force_skip:
        return "skipped_offline"
    fixture_name = check["fixture"]
    if fixture_name not in FIXTURES:
        raise KeyError(f"Unknown fixture: {fixture_name}")
    bf = FIXTURES[fixture_name]
    request = CalculatorRequest(
        attacker=bf.attacker,
        defender=bf.defender,
        move=bf.move,
        conditions=bf.conditions,
    )
    final = orch.handle(
        item["question"],
        context={"calculator_request": request},
    )
    text = final.content
    for needle in check["must_contain"]:
        if needle not in text:
            raise AssertionError(
                f"id={item['id']}: response missing {needle!r}. Got:\n{text[:800]}"
            )
    return "ok"


def main() -> None:
    parser = argparse.ArgumentParser(description="Dataset correctness runner")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(__file__).resolve().parent / "dataset.json",
    )
    parser.add_argument(
        "--require-groq",
        action="store_true",
        help="Exit 1 if orchestrator checks were skipped (offline LLM).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Force offline mode and skip orchestrator checks.",
    )
    args = parser.parse_args()
    orch = Orchestrator(llm=LLMClient(api_key="")) if args.offline else Orchestrator()
    data = _load_dataset(args.dataset)
    ran = 0
    skipped_orch = 0
    for item in data:
        c = item.get("correctness")
        if not c:
            continue
        ctype = c.get("type")
        if ctype == "damage_calculator":
            _run_damage_calculator(c)
            ran += 1
        elif ctype == "orchestrator":
            status = _run_orchestrator(item, c, orch=orch, force_skip=args.offline)
            if status == "skipped_offline":
                skipped_orch += 1
            else:
                ran += 1
        else:
            raise ValueError(f"id={item['id']}: unknown correctness type {ctype!r}")
    msg = f"correctness: OK ({ran} checks"
    if skipped_orch:
        msg += f", {skipped_orch} orchestrator checks skipped (offline LLM)"
    msg += ")"
    print(msg)
    if args.require_groq and skipped_orch:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

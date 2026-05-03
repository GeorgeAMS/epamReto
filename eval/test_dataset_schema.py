"""Validación estática de ``eval/dataset.json`` (sin red ni LLM)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval._fixtures_registry import FIXTURES

_DATASET = Path(__file__).resolve().parent / "dataset.json"
_VALID_CATEGORIES = frozenset({"stats", "calc", "lore", "strategy", "mixed"})


def _load() -> list[dict]:
    data = json.loads(_DATASET.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


def test_dataset_has_thirty_items() -> None:
    data = _load()
    assert len(data) == 30


def test_dataset_ids_are_one_to_thirty() -> None:
    data = _load()
    assert sorted(row["id"] for row in data) == list(range(1, 31))


def test_dataset_schema_and_fixtures() -> None:
    data = _load()
    seen_ids: set[int] = set()
    for item in data:
        assert isinstance(item, dict)
        iid = item["id"]
        assert isinstance(iid, int)
        assert iid not in seen_ids
        seen_ids.add(iid)
        assert item["category"] in _VALID_CATEGORIES
        assert isinstance(item["question"], str) and item["question"].strip()
        assert isinstance(item["ground_truth"], str) and item["ground_truth"].strip()
        ctx = item["contexts"]
        assert isinstance(ctx, list) and len(ctx) >= 1
        assert all(isinstance(c, str) and c.strip() for c in ctx)
        corr = item.get("correctness")
        if corr is None:
            continue
        ctype = corr["type"]
        if ctype == "damage_calculator":
            assert corr["fixture"] in FIXTURES
            assert isinstance(corr["expect_damage"], int)
            r = corr["expect_range"]
            assert isinstance(r, list) and len(r) == 2
            assert isinstance(r[0], int) and isinstance(r[1], int)
        elif ctype == "orchestrator":
            assert corr["fixture"] in FIXTURES
            mc = corr["must_contain"]
            assert isinstance(mc, list) and len(mc) >= 1
            assert all(isinstance(s, str) and s for s in mc)
        else:
            raise AssertionError(f"unknown correctness type: {ctype}")

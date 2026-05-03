"""Tests del DuckDBClient (in-memory)."""

from __future__ import annotations

from pathlib import Path

import pytest

from infrastructure.duckdb_client import DuckDBClient
from shared.errors import InfrastructureError


def test_in_memory_query_round_trip() -> None:
    with DuckDBClient(in_memory=True) as db:
        db.execute("CREATE TABLE pokemon (name VARCHAR, bst INTEGER)")
        db.execute("INSERT INTO pokemon VALUES (?, ?), (?, ?)", ["Garchomp", 600, "Blissey", 540])
        rows = db.query("SELECT name, bst FROM pokemon ORDER BY bst DESC")
        assert rows[0] == {"name": "Garchomp", "bst": 600}
        assert rows[1] == {"name": "Blissey", "bst": 540}


def test_query_one_returns_dict_or_none() -> None:
    with DuckDBClient(in_memory=True) as db:
        db.execute("CREATE TABLE t (x INTEGER)")
        db.execute("INSERT INTO t VALUES (?)", [42])
        first = db.query_one("SELECT x FROM t")
        assert first == {"x": 42}
        empty = db.query_one("SELECT x FROM t WHERE x = 99")
        assert empty is None


def test_exists_detects_table() -> None:
    with DuckDBClient(in_memory=True) as db:
        assert db.exists("missing") is False
        db.execute("CREATE TABLE present (a INTEGER)")
        assert db.exists("present") is True


def test_register_csv_loads_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "p.csv"
    csv_path.write_text("name,bst\nGarchomp,600\nBlissey,540\n", encoding="utf-8")
    with DuckDBClient(in_memory=True) as db:
        n = db.register_csv(csv_path, "pokemon")
        assert n == 2
        rows = db.query("SELECT name FROM pokemon ORDER BY name")
        assert [r["name"] for r in rows] == ["Blissey", "Garchomp"]


def test_register_csv_missing_file_raises(tmp_path: Path) -> None:
    with DuckDBClient(in_memory=True) as db, pytest.raises(InfrastructureError):
        db.register_csv(tmp_path / "missing.csv", "x")


def test_query_error_wraps_as_infrastructure_error() -> None:
    with DuckDBClient(in_memory=True) as db, pytest.raises(InfrastructureError):
        db.query("SELECT * FROM nonexistent")

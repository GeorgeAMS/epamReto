"""Wrapper tipado sobre DuckDB.

DuckDB es perfecto para consultas analíticas sobre los CSVs de Kaggle: el
``stats_agent`` lo usa para responder cosas tipo "top 5 dragones por BST en
generación 9" sin diseñar un esquema relacional formal.

Este módulo expone:
- ``DuckDBClient.query(sql, params)``    → ``list[dict[str, Any]]``
- ``DuckDBClient.query_one(sql, params)``→ ``dict[str, Any] | None``
- ``DuckDBClient.register_csv(...)``     → registra un CSV como tabla en RAM
- ``DuckDBClient.execute(sql, params)``  → DDL (CREATE/INSERT) sin retorno
- ``DuckDBClient.exists(table)``         → bool

Soporta context manager (``with DuckDBClient() as db:``) y modo
``in_memory=True`` para tests/cli.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from types import TracebackType
from typing import Any

import duckdb

from infrastructure.settings import get_settings
from shared.errors import InfrastructureError
from shared.logging import get_logger

log = get_logger(__name__)


class DuckDBClient:
    """Cliente DuckDB sin pretensiones — pero tipado y testeable."""

    def __init__(
        self,
        *,
        path: str | None = None,
        read_only: bool = False,
        in_memory: bool = False,
    ) -> None:
        if in_memory:
            self._path = ":memory:"
        else:
            settings = get_settings()
            db_path = path or settings.duckdb_path
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self._path = db_path
        self._read_only = read_only
        try:
            self._con = duckdb.connect(self._path, read_only=read_only)
        except duckdb.Error as exc:
            raise InfrastructureError(
                "No se pudo conectar a DuckDB",
                details={"path": self._path, "error": str(exc)},
            ) from exc

    # --- lifecycle -------------------------------------------------------

    def close(self) -> None:
        self._con.close()

    def __enter__(self) -> DuckDBClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    # --- API -------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row: tuple[Any, ...], description: list[Any]) -> dict[str, Any]:
        return {col[0]: row[i] for i, col in enumerate(description)}

    def query(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Ejecuta SELECT y devuelve filas como diccionarios."""
        try:
            cursor = self._con.execute(sql, list(params) if params else [])
        except duckdb.Error as exc:
            raise InfrastructureError(
                "Error ejecutando query DuckDB",
                details={"sql": sql, "error": str(exc)},
            ) from exc
        rows = cursor.fetchall()
        description = cursor.description or []
        return [self._row_to_dict(r, description) for r in rows]

    def query_one(
        self,
        sql: str,
        params: Iterable[Any] | None = None,
    ) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> None:
        """DDL/DML sin retorno (CREATE/INSERT/UPDATE/DELETE)."""
        try:
            self._con.execute(sql, list(params) if params else [])
        except duckdb.Error as exc:
            raise InfrastructureError(
                "Error ejecutando comando DuckDB",
                details={"sql": sql, "error": str(exc)},
            ) from exc

    def register_csv(
        self,
        csv_path: str | Path,
        table: str,
        *,
        replace: bool = True,
    ) -> int:
        """Crea una tabla DuckDB a partir de un CSV. Devuelve el número de filas."""
        csv_path_str = str(csv_path)
        if not Path(csv_path_str).exists():
            raise InfrastructureError(
                "CSV no existe",
                details={"path": csv_path_str},
            )
        verb = "CREATE OR REPLACE" if replace else "CREATE"
        self.execute(
            f"{verb} TABLE {table} AS SELECT * FROM read_csv_auto(?)",
            [csv_path_str],
        )
        row = self.query_one(f"SELECT COUNT(*) AS n FROM {table}")
        n = int(row["n"]) if row else 0
        log.info("duckdb.register_csv", csv=csv_path_str, table=table, rows=n)
        return n

    def exists(self, table: str) -> bool:
        rows = self.query(
            "SELECT 1 FROM information_schema.tables WHERE table_name = ?",
            [table],
        )
        return bool(rows)

    @property
    def path(self) -> str:
        return self._path

    @property
    def is_read_only(self) -> bool:
        return self._read_only


__all__ = ["DuckDBClient"]

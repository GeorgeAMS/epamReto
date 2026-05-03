"""Ingesta programática de CSVs Kaggle a DuckDB.

Mientras ``load_kaggle_csv.py`` expone una **CLI** sobre el mismo flujo,
este módulo expone la **función** que la API/scripts llaman directamente
(la firma que pide el spec del proyecto).

Ejemplo::

    from infrastructure.ingestion.csv_ingest import ingest_pokemon_csv

    n = ingest_pokemon_csv("data/raw/pokemon.csv", table="pokemon")
    # → n filas cargadas en `pokemon` dentro de DuckDB.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from infrastructure.duckdb_client import DuckDBClient
from infrastructure.ingestion.load_kaggle_csv import _normalize_columns
from infrastructure.settings import get_settings
from shared.errors import InfrastructureError
from shared.logging import get_logger

log = get_logger(__name__)


def ingest_pokemon_csv(
    source: str | Path,
    *,
    table: str = "pokemon",
    db_path: str | None = None,
    normalize: bool = True,
) -> int:
    """Carga ``source`` como tabla DuckDB; devuelve el número de filas.

    Args:
        source: ruta al CSV (ej. ``data/raw/pokemon.csv``).
        table: nombre de la tabla destino dentro de DuckDB.
        db_path: override del path de la BD; por defecto usa
            ``settings.duckdb_path``.
        normalize: si True, renombra columnas a snake_case canónico
            (mismo mapeo que la CLI ``load_kaggle_csv``).

    Returns:
        Cantidad de filas cargadas.
    """
    settings = get_settings()
    settings.ensure_data_dirs()

    src = Path(source)
    if not src.exists():
        raise InfrastructureError(
            "CSV no existe",
            details={"path": str(src)},
        )

    df = pd.read_csv(src)
    if normalize:
        df = _normalize_columns(df)
    if "name" not in df.columns:
        raise InfrastructureError(
            "El CSV no contiene columna mapeable a 'name'",
            details={"columns": list(df.columns)},
        )

    target_db = db_path or settings.duckdb_path
    with DuckDBClient(path=target_db) as db:
        # Pasamos por DataFrame en memoria — DuckDB lo expone con `register`.
        db._con.register("df_view", df)
        db.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM df_view")
        row = db.query_one(f"SELECT COUNT(*) AS n FROM {table}")
        n = int(row["n"]) if row else 0

    log.info("csv_ingest.done", source=str(src), table=table, rows=n, db=target_db)
    return n


__all__ = ["ingest_pokemon_csv"]

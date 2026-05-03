"""Ingesta de CSVs de Kaggle a DuckDB.

Estrategia: usamos DuckDB porque permite hacer SQL sobre Pandas / Parquet / CSV
sin pipeline ETL pesado. El `stats_agent` puede luego ejecutar consultas
agregadas tipo:

    SELECT name, hp+attack+defense+sp_atk+sp_def+speed AS bst
    FROM pokemon
    WHERE primary_type='dragon'
    ORDER BY bst DESC LIMIT 5;

CLI::

    python -m infrastructure.ingestion.load_kaggle_csv --source data/raw/pokemon.csv

El CSV se asume con columnas razonables (case-insensitive, autocompletadas).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import typer
from rich.console import Console

from infrastructure.settings import get_settings
from shared.errors import InfrastructureError
from shared.logging import configure_logging, get_logger

log = get_logger(__name__)
console = Console()

cli = typer.Typer(help="Carga CSVs Kaggle a DuckDB")


_EXPECTED_COLUMNS_MAP: dict[str, str] = {
    # Snake-case canónico → posibles aliases del CSV (lower-cased)
    "id": "id|#|pokedex_number|number",
    "name": "name|pokemon|pokemon_name",
    "primary_type": "type 1|type1|primary_type|type_1",
    "secondary_type": "type 2|type2|secondary_type|type_2",
    "hp": "hp|stat_hp",
    "attack": "attack|atk",
    "defense": "defense|def",
    "sp_atk": "sp. atk|sp_atk|special_attack|sp_attack",
    "sp_def": "sp. def|sp_def|special_defense|sp_defense",
    "speed": "speed|spe",
    "generation": "generation|gen",
    "is_legendary": "legendary|is_legendary",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Renombra columnas del CSV a snake_case canónico tolerando aliases."""
    lower_map = {c: c.lower().strip() for c in df.columns}
    renamed: dict[str, str] = {}
    for canonical, aliases in _EXPECTED_COLUMNS_MAP.items():
        candidates = aliases.split("|")
        for original, lowered in lower_map.items():
            if lowered in candidates:
                renamed[original] = canonical
                break
    return df.rename(columns=renamed)


@cli.command("load")
def load_csv(
    source: Path = typer.Option(..., exists=True, dir_okay=False, help="Ruta al CSV"),
    table: str = typer.Option("pokemon", help="Nombre de la tabla destino"),
    db_path: Path | None = typer.Option(None, help="Override del DUCKDB_PATH"),
) -> None:
    """Carga ``source`` en la tabla ``table`` de DuckDB."""
    configure_logging(level="INFO", json_logs=False)
    settings = get_settings()
    settings.ensure_data_dirs()

    db = str(db_path) if db_path else settings.duckdb_path

    df = pd.read_csv(source)
    df = _normalize_columns(df)
    if "name" not in df.columns:
        raise InfrastructureError(
            "El CSV no contiene columna mapeable a 'name'",
            details={"columns": list(df.columns)},
        )

    log.info("ingest.csv", rows=len(df), table=table, db=db)
    con = duckdb.connect(db)
    try:
        con.register("df_view", df)
        con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM df_view")
        rows = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        count = rows[0] if rows else 0
        console.print(f"[green]OK[/green] {count} filas cargadas en `{table}` ({db}).")
    finally:
        con.close()


@cli.command("query")
def query_db(
    sql: str = typer.Argument(..., help="Consulta SQL (entrecomillada)"),
    db_path: Path | None = typer.Option(None, help="Override del DUCKDB_PATH"),
) -> None:
    """Ejecuta SQL ad-hoc contra la BD para validar la ingesta."""
    settings = get_settings()
    db = str(db_path) if db_path else settings.duckdb_path
    con = duckdb.connect(db, read_only=True)
    try:
        df = con.execute(sql).fetchdf()
        console.print(df.to_string(index=False))
    finally:
        con.close()


if __name__ == "__main__":
    cli()

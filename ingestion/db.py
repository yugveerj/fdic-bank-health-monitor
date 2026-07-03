"""DuckDB warehouse helpers: connection + idempotent upserts.

Local dev writes to a .duckdb file (gitignored). The same code targets MotherDuck
when MOTHERDUCK_TOKEN is set and the database path is a md: URI.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd

DEFAULT_DB_PATH = "warehouse.duckdb"


def connect(db_path: str | None = None) -> duckdb.DuckDBPyConnection:
    """Open the warehouse. Precedence: explicit arg > FDIC_DB_PATH env > local default."""
    target = db_path or os.environ.get("FDIC_DB_PATH", DEFAULT_DB_PATH)
    if not target.startswith("md:"):
        Path(target).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(target)


def upsert(
    con: duckdb.DuckDBPyConnection,
    table: str,
    df: pd.DataFrame,
    keys: list[str],
) -> int:
    """Delete-then-insert by key: safe to re-run with overlapping data.

    Creates the table from the frame's schema on first load. Returns rows written.
    """
    if df.empty:
        return 0
    missing = [k for k in keys if k not in df.columns]
    if missing:
        raise ValueError(f"key column(s) {missing} not in dataframe for {table}")
    if df.duplicated(subset=keys).any():
        raise ValueError(f"duplicate keys within incoming batch for {table}")

    con.register("_incoming", df)
    con.execute(f'CREATE TABLE IF NOT EXISTS "{table}" AS SELECT * FROM _incoming WHERE 1=0')
    predicate = " AND ".join(f't."{k}" = i."{k}"' for k in keys)
    con.execute(
        f'DELETE FROM "{table}" t WHERE EXISTS (SELECT 1 FROM _incoming i WHERE {predicate})'
    )
    con.execute(f'INSERT INTO "{table}" SELECT * FROM _incoming')
    con.unregister("_incoming")
    return len(df)


def row_count(con: duckdb.DuckDBPyConnection, table: str) -> int:
    return con.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]

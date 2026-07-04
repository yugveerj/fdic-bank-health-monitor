"""Build a small warehouse from the committed fixture parquets so CI can run
the full dbt project without touching the FDIC API or any secrets.

The fixture rows are real API data for five banks (extracted once from a full
ingest), plus an empty FRED table with the right schema.

Usage: uv run python -m scripts.build_ci_warehouse [target.duckdb]
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).parent.parent
FIXTURES = ROOT / "tests" / "fixtures"


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "ci_warehouse.duckdb"
    target.unlink(missing_ok=True)
    con = duckdb.connect(str(target))
    try:
        for table in ("raw_fdic_financials", "raw_fdic_institutions", "raw_fdic_failures"):
            con.execute(
                f"CREATE TABLE {table} AS SELECT * FROM read_parquet('{FIXTURES / table}.parquet')"
            )
            n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            print(f"{table}: {n} fixture rows")
        con.execute(
            "CREATE TABLE raw_fred_h8 (series_id VARCHAR, series_title VARCHAR,"
            " obs_date VARCHAR, value VARCHAR)"
        )
    finally:
        con.close()
    print(f"CI warehouse written to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

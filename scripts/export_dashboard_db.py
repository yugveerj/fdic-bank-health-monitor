"""Export the dashboard-facing marts from the warehouse into a small DuckDB file
the Evidence build reads. This decouples dashboard builds from the FDIC API
entirely: pushes rebuild the site from the warehouse (local file in dev,
MotherDuck in CI via FDIC_DB_PATH) — only the scheduled refresh re-ingests.

Usage: uv run python scripts/export_dashboard_db.py
"""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

from dotenv import load_dotenv

from ingestion.db import connect

log = logging.getLogger(__name__)

EXPORT_PATH = Path(__file__).parent.parent / "dashboard" / "sources" / "fdic" / "fdic.duckdb"
TABLES = ["dim_banks", "fct_bank_quarters", "mart_outlier_flags", "mart_peer_percentiles"]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_PATH.unlink(missing_ok=True)

    con = connect()
    try:
        con.execute(f"ATTACH '{EXPORT_PATH}' AS export")
        for table in TABLES:
            con.execute(f"CREATE TABLE export.{table} AS SELECT * FROM {table}")
            n = con.execute(f"SELECT count(*) FROM export.{table}").fetchone()[0]
            log.info("exported %s: %d rows", table, n)
        con.execute(
            """
            CREATE TABLE export.build_meta AS
            SELECT
                ?::timestamp AS built_at,
                (SELECT max(report_date) FROM fct_bank_quarters)  AS freshest_quarter,
                (SELECT count(*) FROM fct_bank_quarters)          AS bank_quarters,
                (SELECT count(*) FROM dim_banks)                  AS banks,
                (SELECT count(*) FROM dim_banks WHERE is_active)  AS active_banks
            """,
            [dt.datetime.now(dt.UTC)],
        )
    finally:
        con.close()
    log.info("export written to %s (%.1f MB)", EXPORT_PATH, EXPORT_PATH.stat().st_size / 1e6)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

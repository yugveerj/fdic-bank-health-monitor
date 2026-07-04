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
# export name -> relation in the warehouse (marts are tables, fred staging is a view)
TABLES = {
    "dim_banks": "dim_banks",
    "fct_bank_quarters": "fct_bank_quarters",
    "mart_outlier_flags": "mart_outlier_flags",
    "mart_peer_percentiles": "mart_peer_percentiles",
    "fred_h8": "stg_fred__h8",
}


def _export_quality_status(con) -> None:
    """Status rows for the data-quality page, each derived from a build artifact
    or a live warehouse query at export time. Rows that can't be derived are
    omitted rather than hardcoded."""
    import json

    rows: list[tuple[str, str, str]] = []

    run_results = Path(__file__).parent.parent / "dbt" / "target" / "run_results.json"
    if run_results.exists():
        results = json.loads(run_results.read_text())["results"]
        tests = [r for r in results if r["unique_id"].startswith("test.")]
        passed = sum(1 for r in tests if r["status"] == "pass")
        failed = sum(1 for r in tests if r["status"] in ("fail", "error"))
        rows.append((
            "dbt tests",
            f"{passed} passed, {failed} failed",
            "unique keys, relationships, accepted ranges, custom checks",
        ))

    latest, prior, n_latest, n_prior = con.execute(
        """
        WITH q AS (SELECT DISTINCT report_date FROM fct_bank_quarters ORDER BY 1 DESC LIMIT 2)
        SELECT (SELECT max(report_date) FROM q), (SELECT min(report_date) FROM q),
               (SELECT count(*) FROM fct_bank_quarters WHERE report_date = (SELECT max(report_date) FROM q)),
               (SELECT count(*) FROM fct_bank_quarters WHERE report_date = (SELECT min(report_date) FROM q))
        """
    ).fetchone()
    rows.append(("Latest FDIC quarter", str(latest), "quarterly data lands ~60 days after quarter-end"))
    rows.append((
        "Banks reporting, latest quarter",
        f"{n_latest:,}",
        f"prior quarter ({prior}): {n_prior:,}",
    ))

    fred_latest = con.execute("SELECT max(obs_date) FROM stg_fred__h8").fetchone()[0]
    if fred_latest is not None:
        rows.append(("Latest FRED H.8 observation", str(fred_latest), "weekly, refreshed Saturdays"))

    dup_raw = con.execute(
        "SELECT count(*) FROM (SELECT CERT, REPDTE FROM raw_fdic_financials GROUP BY 1,2 HAVING count(*) > 1)"
    ).fetchone()[0]
    dup_fct = con.execute(
        "SELECT count(*) FROM (SELECT bank_quarter_key FROM fct_bank_quarters GROUP BY 1 HAVING count(*) > 1)"
    ).fetchone()[0]
    rows.append(("Duplicate keys", f"{dup_raw + dup_fct}", "raw financials and fact grain, checked at export"))

    orphan_certs, orphan_rows = con.execute(
        """SELECT count(DISTINCT f.CERT), count(*) FROM raw_fdic_financials f
           WHERE f.CERT NOT IN (SELECT CERT FROM raw_fdic_institutions)"""
    ).fetchone()
    rows.append((
        "Excluded: filers outside the FDIC registry",
        f"{orphan_certs} filers ({orphan_rows} bank-quarters)",
        "insured non-bank filers; kept in raw, excluded from analysis",
    ))
    assistance = con.execute(
        "SELECT count(*) FROM raw_fdic_failures WHERE RESTYPE = 'ASSISTANCE'"
    ).fetchone()[0]
    rows.append((
        "Excluded: assistance records not counted as failures",
        f"{assistance:,}",
        "open-bank assistance events in the failures feed",
    ))
    null_cert = con.execute(
        "SELECT count(*) FROM raw_fdic_failures WHERE CERT IS NULL"
    ).fetchone()[0]
    rows.append((
        "Failure records with no certificate number",
        f"{null_cert:,}",
        "Depression-era records; keyed on the API's own ID",
    ))

    import pandas as pd

    df = pd.DataFrame(rows, columns=["check", "value", "detail"])
    con.register("_quality", df)
    con.execute("CREATE TABLE export.quality_status AS SELECT * FROM _quality")
    con.unregister("_quality")
    log.info("exported quality_status: %d rows", len(df))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_PATH.unlink(missing_ok=True)

    con = connect()
    try:
        con.execute(f"ATTACH '{EXPORT_PATH}' AS export")
        for name, relation in TABLES.items():
            con.execute(f"CREATE TABLE export.{name} AS SELECT * FROM {relation}")
            n = con.execute(f"SELECT count(*) FROM export.{name}").fetchone()[0]
            log.info("exported %s: %d rows", name, n)
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
        _export_quality_status(con)
    finally:
        con.close()
    log.info("export written to %s (%.1f MB)", EXPORT_PATH, EXPORT_PATH.stat().st_size / 1e6)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

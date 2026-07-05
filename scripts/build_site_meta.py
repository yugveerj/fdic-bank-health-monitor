"""Materialize the two dashboard-only tables in BigQuery: build_meta (the
site header's freshness numbers) and quality_status (the data-quality page's
checks). These were created inside the exported fdic.duckdb before the
BigQuery cutover; now Evidence reads the warehouse directly, so they live as
real tables beside the marts, rebuilt on every deploy after dbt build.

Rows that can't be derived are omitted rather than hardcoded — same contract
as the DuckDB-era exporter.

Usage: uv run python -m scripts.build_site_meta
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery

log = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent


def _one(client: bigquery.Client, sql: str) -> tuple:
    return tuple(next(iter(client.query_and_wait(sql))))


def quality_rows(client: bigquery.Client, marts: str, raw: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []

    run_results = ROOT / "dbt" / "target" / "run_results.json"
    if run_results.exists():
        results = json.loads(run_results.read_text())["results"]
        tests = [r for r in results if r["unique_id"].startswith("test.")]
        # `dbt build` records a passing test as "pass", but if the last thing to
        # write run_results.json was `dbt docs generate` (as it is in the deploy
        # job) the same rows read "success" — count both so the published figure
        # doesn't silently collapse to "0 passed, 0 failed".
        passed = sum(1 for r in tests if r["status"] in ("pass", "success"))
        failed = sum(1 for r in tests if r["status"] in ("fail", "error"))
        rows.append((
            "dbt tests",
            f"{passed} passed, {failed} failed",
            "unique keys, relationships, accepted ranges, custom checks",
        ))

    latest, prior, n_latest, n_prior = _one(client, f"""
        WITH q AS (SELECT DISTINCT report_date FROM `{marts}.fct_bank_quarters`
                   ORDER BY 1 DESC LIMIT 2)
        SELECT (SELECT max(report_date) FROM q), (SELECT min(report_date) FROM q),
               (SELECT count(*) FROM `{marts}.fct_bank_quarters`
                WHERE report_date = (SELECT max(report_date) FROM q)),
               (SELECT count(*) FROM `{marts}.fct_bank_quarters`
                WHERE report_date = (SELECT min(report_date) FROM q))
        """)
    rows.append(("Latest FDIC quarter", str(latest), "quarterly data lands ~60 days after quarter-end"))
    n_active = _one(client, f"""
        SELECT count(*) FROM `{marts}.fct_bank_quarters` f
        JOIN `{marts}.dim_banks` d USING (cert)
        WHERE f.report_date = (SELECT max(report_date) FROM `{marts}.fct_bank_quarters`)
          AND d.is_active""")[0]
    rows.append((
        "Banks reporting, latest quarter",
        f"{n_latest:,} ({n_active:,} active)",
        f"prior quarter ({prior}): {n_prior:,}",
    ))

    fred_latest = _one(client, f"SELECT max(obs_date) FROM `{marts}.stg_fred__h8`")[0]
    if fred_latest is not None:
        rows.append(("Latest FRED H.8 observation", str(fred_latest), "weekly, refreshed Saturdays"))

    dup_raw = _one(client, f"""
        SELECT count(*) FROM (SELECT CERT, REPDTE FROM `{raw}.raw_fdic_financials`
                              GROUP BY 1, 2 HAVING count(*) > 1)""")[0]
    dup_fct = _one(client, f"""
        SELECT count(*) FROM (SELECT bank_quarter_key FROM `{marts}.fct_bank_quarters`
                              GROUP BY 1 HAVING count(*) > 1)""")[0]
    rows.append(("Duplicate keys", f"{dup_raw + dup_fct}", "raw financials and fact grain, checked at export"))

    orphan_certs, orphan_rows = _one(client, f"""
        SELECT count(DISTINCT f.CERT), count(*) FROM `{raw}.raw_fdic_financials` f
        WHERE f.CERT NOT IN (SELECT CERT FROM `{raw}.raw_fdic_institutions`)""")
    rows.append((
        "Excluded: filers outside the FDIC registry",
        f"{orphan_certs} filers ({orphan_rows} bank-quarters)",
        "insured non-bank filers; kept in raw, excluded from analysis",
    ))
    assistance = _one(client, f"""
        SELECT count(*) FROM `{raw}.raw_fdic_failures` WHERE RESTYPE = 'ASSISTANCE'""")[0]
    rows.append((
        "Excluded: assistance records not counted as failures",
        f"{assistance:,}",
        "open-bank assistance events in the failures feed",
    ))
    null_cert = _one(client, f"""
        SELECT count(*) FROM `{raw}.raw_fdic_failures` WHERE CERT IS NULL""")[0]
    rows.append((
        "Failure records with no certificate number",
        f"{null_cert:,}",
        "Depression-era records; keyed on the API's own ID",
    ))
    return rows


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    project = os.environ.get("GCP_PROJECT")
    if not project:
        raise SystemExit("GCP_PROJECT is not set — see .env.example")
    marts = f"{project}.{os.environ.get('BQ_MARTS_DATASET', 'analytics')}"
    raw = f"{project}.{os.environ.get('BQ_RAW_DATASET', 'fdic_raw')}"

    client = bigquery.Client(project=project)
    try:
        client.query_and_wait(f"""
            CREATE OR REPLACE TABLE `{marts}.build_meta` AS
            SELECT
                current_timestamp()                                            AS built_at,
                (SELECT max(report_date) FROM `{marts}.fct_bank_quarters`)     AS freshest_quarter,
                (SELECT count(*) FROM `{marts}.fct_bank_quarters`)             AS bank_quarters,
                (SELECT count(*) FROM `{marts}.dim_banks`)                     AS banks,
                (SELECT count(*) FROM `{marts}.dim_banks` WHERE is_active)     AS active_banks
            """)
        log.info("built %s.build_meta", marts)

        df = pd.DataFrame(quality_rows(client, marts, raw), columns=["check", "value", "detail"])
        job = client.load_table_from_dataframe(
            df,
            f"{marts}.quality_status",
            job_config=bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
            ),
        )
        job.result()
        log.info("built %s.quality_status: %d rows", marts, len(df))
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

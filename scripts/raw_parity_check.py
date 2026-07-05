"""Phase A raw parity: BigQuery `fdic_raw` vs the current DuckDB/MotherDuck
warehouse. Row counts must match exactly — per quarter (REPDTE) for financials,
per series+week for FRED, whole-table for the snapshot tables. Prints the
comparison as a markdown table and exits nonzero on any unexplained mismatch.

One tolerated asymmetry: rows that exist only in BigQuery AND are newer than
the old warehouse's high-water mark. The scheduled production refresh and a
branch ingest never run at the same instant, so the fresher side is expected
to be ahead on weekly FRED data (and on a quarter boundary, financials). The
overlap still has to match exactly — that is what proves the load path.
Anything missing from BigQuery, or differing inside the overlap, fails.

The DuckDB side connects exactly as production does (FDIC_DB_PATH, e.g.
md:fdic_bank_health in CI); the BigQuery side via GCP_PROJECT/BQ_RAW_DATASET.

Usage: uv run python -m scripts.raw_parity_check
"""

from __future__ import annotations

import logging
import sys

from dotenv import load_dotenv

from ingestion import bq
from ingestion.db import connect as duck_connect

log = logging.getLogger(__name__)

# table -> columns to group counts by (None = whole-table snapshot count).
# Date-like column first: slice keys sort lexically, and both REPDTE (YYYYMMDD)
# and obs_date (YYYY-MM-DD) sort chronologically, which the tail rule needs.
GROUPED = {
    "raw_fdic_financials": ["REPDTE"],
    "raw_fred_h8": ["obs_date", "series_id"],
    "raw_fdic_institutions": None,
    "raw_fdic_failures": None,
}


def duck_counts(con, table: str, group: list[str] | None) -> dict[str, int]:
    if group is None:
        return {table: con.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]}
    cols = ", ".join(f'CAST("{c}" AS VARCHAR)' for c in group)
    rows = con.execute(f'SELECT {cols}, count(*) FROM "{table}" GROUP BY ALL').fetchall()
    return {" ".join(r[:-1]): r[-1] for r in rows}


def bq_counts(wh: bq.Warehouse, table: str, group: list[str] | None) -> dict[str, int]:
    if group is None:
        return {table: bq.row_count(wh, table)}
    cols = ", ".join(f"CAST(`{c}` AS STRING)" for c in group)
    rows = wh.client.query_and_wait(
        f"SELECT {cols}, count(*) FROM {wh.qualified(table)} GROUP BY ALL"
    )
    return {" ".join(t[:-1]): t[-1] for t in (tuple(r) for r in rows)}


def compare(table: str, old: dict[str, int], new: dict[str, int]) -> tuple[list[str], bool]:
    """Rows for the report and whether this table passes. Keys sort lexically,
    which is chronological for both REPDTE (YYYYMMDD) and obs_date (YYYY-MM-DD)."""
    lines, ok = [], True
    if not old:
        # nothing to compare against is a failure, not a vacuous pass — the
        # tail rule below would otherwise wave every slice through as "ahead"
        total_new = sum(new.values())
        return [f"| {table} | (old warehouse empty) | 0 | {total_new} | MISMATCH |"], False
    high_water = max(old)
    for key in sorted(set(old) | set(new)):
        o, n = old.get(key), new.get(key)
        if o == n:
            status = "match"
        elif o is None and key > high_water:
            status = "bigquery ahead (newer than warehouse high-water — OK)"
        else:
            status, ok = "MISMATCH", False
        lines.append(f"| {table} | {key} | {'' if o is None else o} | "
                     f"{'' if n is None else n} | {status} |")
    return lines, ok


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    con = duck_connect()
    wh = bq.connect()
    all_ok = True
    report = [
        "| table | slice | old warehouse | bigquery | status |",
        "| --- | --- | --- | --- | --- |",
    ]
    try:
        for table, group in GROUPED.items():
            lines, ok = compare(table, duck_counts(con, table, group), bq_counts(wh, table, group))
            report.extend(lines)
            all_ok &= ok
            log.info("%s: %s", table, "parity" if ok else "MISMATCH")
    finally:
        con.close()
        wh.close()
    print("\n".join(report))
    print(f"\nraw parity: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

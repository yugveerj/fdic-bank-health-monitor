"""Phase B mart parity: every mart rebuilt on BigQuery vs the current
production (MotherDuck) marts. The gate that blocks cutover:

- row counts per mart match
- key sets match exactly (anti-join both directions)
- every numeric cell agrees within 1e-9 absolute; everything else exactly

Prints a per-mart summary plus the worst offender per column on failure, and
exits nonzero on any difference. Results are recorded in
docs/migration_validation.md; unexplained drift stops the migration.

DuckDB side via FDIC_DB_PATH (md:fdic_bank_health in CI); BigQuery side via
GCP_PROJECT + BQ_MARTS_DATASET (default dbt_dev — the branch-built marts).

Usage: uv run python -m scripts.mart_parity_check
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import sys

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery

from ingestion.db import connect as duck_connect

log = logging.getLogger(__name__)

ATOL = 1e-9

# mart -> key columns (grain per dbt schema tests)
MARTS = {
    "dim_banks": ["cert"],
    "fct_bank_quarters": ["cert", "report_date"],
    "mart_outlier_flags": ["cert", "report_date"],
    "mart_peer_percentiles": ["cert", "report_date", "metric"],
    "mart_model_percentiles": ["cert", "report_date", "metric"],
}


def _normalize(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Key columns to strings (dates/ints render identically on both engines),
    sorted, key-indexed. Data columns keep their dtypes for typed comparison."""
    for k in keys:
        df[k] = df[k].astype(str)
    if df.duplicated(subset=keys).any():
        raise SystemExit(f"duplicate keys in one side of the comparison ({keys})")
    return df.set_index(keys).sort_index()


def _is_float(a: pd.Series, b: pd.Series) -> bool:
    return any(str(s.dtype).lower().startswith("float") for s in (a, b))


def _as_objects(s: pd.Series) -> pd.Series:
    """Comparable object values: NULLs (NaN/NaT/pd.NA) become None and every
    date-like becomes its ISO string — duckdb serves DATE columns as
    datetime64 Timestamps while BigQuery serves date objects, and those never
    compare equal however identical the dates."""
    if str(s.dtype).startswith("datetime64") or str(s.dtype) == "dbdate":
        return s.map(lambda v: None if pd.isna(v) else pd.Timestamp(v).date().isoformat())
    out = s.astype(object).where(s.notna(), None)
    return out.map(
        lambda v: pd.Timestamp(v).date().isoformat()
        if isinstance(v, (dt.date, dt.datetime, pd.Timestamp))
        else v
    )


def compare_mart(mart: str, old: pd.DataFrame, new: pd.DataFrame, keys: list[str]) -> dict:
    result = {"mart": mart, "rows_old": len(old), "rows_new": len(new), "problems": []}
    if set(old.columns) != set(new.columns):
        result["problems"].append(
            f"column sets differ: only-old={sorted(set(old.columns) - set(new.columns))} "
            f"only-new={sorted(set(new.columns) - set(old.columns))}"
        )
        return result
    old, new = _normalize(old, keys), _normalize(new, keys)
    only_old, only_new = old.index.difference(new.index), new.index.difference(old.index)
    if len(only_old) or len(only_new):
        result["problems"].append(
            f"key sets differ: {len(only_old)} only in production, {len(only_new)} only in "
            f"bigquery (e.g. {list(only_old[:3]) + list(only_new[:3])})"
        )
        return result
    new = new.loc[old.index]

    max_float_diff = 0.0
    for col in old.columns:
        a, b = old[col], new[col]
        if _is_float(a, b):
            av = a.astype("float64").to_numpy()
            bv = b.astype("float64").to_numpy()
            ok = np.isclose(av, bv, rtol=0, atol=ATOL, equal_nan=True)
            diffs = np.abs(av - bv)
            finite = diffs[~np.isnan(diffs)]
            max_float_diff = max(max_float_diff, float(finite.max()) if len(finite) else 0.0)
            if not ok.all():
                # the genuinely worst failing cell; NaN-vs-value failures have
                # no magnitude, so fall back to the first failure if that's all
                ranked = np.where(np.isnan(diffs) | ok, -np.inf, diffs)
                i = int(np.argmax(ranked))
                if not np.isfinite(ranked[i]):
                    i = int(np.argmin(ok))
                result["problems"].append(
                    f"{col}: {int((~ok).sum())} cells beyond {ATOL} "
                    f"(worst at {old.index[i]}: {av[i]!r} vs {bv[i]!r})"
                )
        else:
            av, bv = _as_objects(a), _as_objects(b)
            # pandas missing-value semantics make None != None come out True;
            # a NULL on both sides is agreement, not drift
            neq = (av != bv) & ~(av.isna() & bv.isna())
            if neq.any():
                i = int(np.argmax(neq.to_numpy()))
                result["problems"].append(
                    f"{col}: {int(neq.sum())} cells differ exactly "
                    f"(e.g. at {old.index[i]}: {av.iloc[i]!r} vs {bv.iloc[i]!r})"
                )
    result["max_float_diff"] = max_float_diff
    return result


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    project = os.environ.get("GCP_PROJECT")
    if not project:
        raise SystemExit("GCP_PROJECT is not set — see .env.example")
    dataset = os.environ.get("BQ_MARTS_DATASET", "dbt_dev")

    con = duck_connect()
    client = bigquery.Client(project=project)
    all_ok = True
    try:
        for mart, keys in MARTS.items():
            old = con.execute(f'SELECT * FROM "{mart}"').df()
            new = client.query_and_wait(f"SELECT * FROM `{project}.{dataset}.{mart}`").to_dataframe()
            r = compare_mart(mart, old, new, keys)
            status = "PASS" if not r["problems"] and r["rows_old"] == r["rows_new"] else "FAIL"
            all_ok &= status == "PASS"
            log.info(
                "%s: %s (%d vs %d rows, max float diff %.2e)",
                mart, status, r["rows_old"], r["rows_new"], r.get("max_float_diff", 0.0),
            )
            for p in r["problems"]:
                log.error("  %s: %s", mart, p)
    finally:
        con.close()
        client.close()
    print(f"\nmart parity: {'PASS' if all_ok else 'FAIL'} (tolerance {ATOL} absolute)")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

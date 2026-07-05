"""Export the two Tableau extracts to the shared Google Sheet: the current
quarter's peer percentiles and twelve quarters of bank trends. Tableau Public
connects to the Sheet and refreshes daily; this export runs on every deploy
after dbt, so the Sheet always mirrors the published marts.

Columns are trimmed to what the two Tableau dashboards actually use — the
Sheet has a 10M-cell ceiling and no business being a warehouse. Values are
peer-relative statistics from public filings, same neutrality rules as
everywhere else.

Auth is ADC (WIF in CI) with the spreadsheets scope; the Sheet is shared to
the service account. Usage: uv run python -m reporting.tableau_sheet
"""

from __future__ import annotations

import logging
import os
import sys

import google.auth
import gspread
import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery

log = logging.getLogger(__name__)

CELL_BUDGET = 2_000_000  # hard stop well under the Sheet's 10M-cell ceiling
TREND_QUARTERS = 12

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def fetch_frames(client: bigquery.Client, marts: str) -> dict[str, pd.DataFrame]:
    peer = client.query_and_wait(f"""
        SELECT
            p.cert,
            b.bank_name,
            p.peer_band,
            p.metric,
            round(p.value, 6)       AS value,
            round(p.robust_z, 4)    AS robust_z,
            round(p.peer_median, 6) AS peer_median
        FROM `{marts}.mart_peer_percentiles` p
        JOIN `{marts}.dim_banks` b USING (cert)
        WHERE p.report_date = (SELECT max(report_date)
                               FROM `{marts}.mart_peer_percentiles`)
        ORDER BY p.peer_band, p.metric, p.robust_z DESC
        """).to_dataframe()

    trends = client.query_and_wait(f"""
        SELECT
            f.cert,
            b.bank_name,
            f.report_date,
            f.peer_band,
            f.business_model,
            round(f.total_assets / 1e6, 3)          AS total_assets_bn,
            round(f.roa_pct, 4)                     AS roa_pct,
            round(f.net_interest_margin_pct, 4)     AS net_interest_margin_pct,
            round(f.equity_to_assets, 6)            AS equity_to_assets,
            round(f.uninsured_deposit_share, 6)     AS uninsured_deposit_share,
            round(f.brokered_deposit_share, 6)      AS brokered_deposit_share,
            round(f.securities_to_assets, 6)        AS securities_to_assets,
            round(f.loans_to_deposits, 6)           AS loans_to_deposits,
            round(f.efficiency_ratio_pct, 4)        AS efficiency_ratio_pct,
            round(f.noncurrent_loans_ratio_pct, 4)  AS noncurrent_loans_ratio_pct
        FROM `{marts}.fct_bank_quarters` f
        JOIN `{marts}.dim_banks` b USING (cert)
        WHERE f.report_date >= (
            SELECT min(report_date) FROM (
                SELECT DISTINCT report_date FROM `{marts}.fct_bank_quarters`
                ORDER BY report_date DESC LIMIT {TREND_QUARTERS}))
        ORDER BY f.cert, f.report_date
        """).to_dataframe()

    return {"peer_percentiles": peer, "bank_trends": trends}


def as_rows(df: pd.DataFrame) -> list[list]:
    """Sheets-safe values: header row first, NaN as empty, dates as ISO
    strings, numpy scalars as plain Python."""
    out = [list(df.columns)]
    for record in df.itertuples(index=False):
        row = []
        for v in record:
            if pd.isna(v):
                row.append("")
            elif hasattr(v, "isoformat"):
                row.append(pd.Timestamp(v).date().isoformat())
            elif hasattr(v, "item"):
                row.append(v.item())
            else:
                row.append(v)
        out.append(row)
    return out


def push(sheet_id: str, frames: dict[str, pd.DataFrame]) -> None:
    total_cells = sum((len(df) + 1) * len(df.columns) for df in frames.values())
    if total_cells > CELL_BUDGET:
        raise SystemExit(f"extract is {total_cells:,} cells — over the {CELL_BUDGET:,} budget; trim columns")

    creds, _ = google.auth.default(scopes=SCOPES)
    sh = gspread.authorize(creds).open_by_key(sheet_id)
    existing = {ws.title: ws for ws in sh.worksheets()}
    for name, df in frames.items():
        rows = as_rows(df)
        ws = existing.get(name) or sh.add_worksheet(name, rows=len(rows), cols=len(df.columns))
        ws.clear()
        ws.update(rows, value_input_option="RAW")
        log.info("wrote worksheet %s: %d rows x %d cols", name, len(rows) - 1, len(df.columns))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    project = os.environ.get("GCP_PROJECT")
    sheet_id = os.environ.get("TABLEAU_SHEET_ID")
    if not project or not sheet_id:
        raise SystemExit("GCP_PROJECT and TABLEAU_SHEET_ID must be set")
    marts = f"{project}.{os.environ.get('BQ_MARTS_DATASET', 'analytics')}"

    client = bigquery.Client(project=project)
    try:
        frames = fetch_frames(client, marts)
    finally:
        client.close()
    push(sheet_id, frames)
    return 0


if __name__ == "__main__":
    sys.exit(main())

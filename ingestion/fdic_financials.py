"""Quarterly financials for every institution over $1B in assets, 2019-Q1 → present.

One request per quarter-end (each quarter is well under the 10k page cap, and
fetch_all paginates anyway if that ever changes). Failed and merged banks stay
in scope automatically: the ASSET filter is applied per quarter, so a bank that
reported > $1B in 2021 and died in 2023 is present for every quarter it filed.
"""

from __future__ import annotations

import datetime as dt
import logging

import pandas as pd

from ingestion.bq import upsert
from ingestion.client import FdicClient
from ingestion.config import FINANCIAL_FIELDS, FIRST_QUARTER_END, MIN_ASSET_THOUSANDS

log = logging.getLogger(__name__)

TABLE = "raw_fdic_financials"
KEYS = ["CERT", "REPDTE"]


def quarter_ends(start: str = FIRST_QUARTER_END, today: dt.date | None = None) -> list[str]:
    """Quarter-end dates from `start` through today, as YYYYMMDD strings
    (the API's REPDTE format — dashed dates silently match nothing)."""
    today = today or dt.date.today()
    first = dt.date.fromisoformat(start)
    out = []
    for year in range(first.year, today.year + 1):
        for month, day in ((3, 31), (6, 30), (9, 30), (12, 31)):
            q = dt.date(year, month, day)
            if first <= q <= today:
                out.append(q.strftime("%Y%m%d"))
    return out


def ingest(client: FdicClient, wh) -> int:
    written = 0
    for q in quarter_ends():
        rows = client.fetch_all(
            "/financials",
            fields=FINANCIAL_FIELDS,
            filters=f"REPDTE:{q} AND ASSET:[{MIN_ASSET_THOUSANDS} TO *]",
            sort_by="CERT",
        )
        if not rows:
            log.info("financials %s: no rows (quarter not yet published)", q)
            continue
        df = pd.DataFrame(rows).reindex(columns=FINANCIAL_FIELDS)
        written += upsert(wh, TABLE, df, KEYS)
        log.info("financials %s: %d rows", q, len(df))
    return written

"""Weekly FRED H.8 aggregates (series selected from the official release page —
see docs/fred_h8_series.md). Every run re-validates each series ID against its
live metadata: if an ID stops resolving or its title drifts, this fails loudly
rather than ingesting mystery data.

Without FRED_API_KEY (local dev), it creates the empty raw table so dbt builds,
warns, and exits cleanly — CI carries the key and ingests for real.
Runnable alone: python -m ingestion.fred_h8
"""

from __future__ import annotations

import logging
import os
import time

import httpx
import pandas as pd

from ingestion import cache
from ingestion.db import connect, upsert

log = logging.getLogger(__name__)

BASE_URL = "https://api.stlouisfed.org/fred"
PAUSE_SECONDS = 0.5
TABLE = "raw_fred_h8"
KEYS = ["series_id", "obs_date"]

# series_id -> official title as recorded from the release page (2026-07-03);
# validated against live metadata on every run
SERIES = {
    "DPSACBW027SBOG": "Deposits, All Commercial Banks",
    "TOTBKCR": "Bank Credit, All Commercial Banks",
    "TOTCI": "Commercial and Industrial Loans, All Commercial Banks",
    "TLAACBW027SBOG": "Total Assets, All Commercial Banks",
}

OBSERVATION_START = "2019-01-01"  # match the FDIC panel's start


def _get(client: httpx.Client, endpoint: str, params: dict) -> dict:
    cached = cache.load(f"/fred{endpoint}", params)
    if cached is not None:
        return cached
    key = os.environ["FRED_API_KEY"]
    resp = client.get(endpoint, params={**params, "api_key": key, "file_type": "json"})
    resp.raise_for_status()
    time.sleep(PAUSE_SECONDS)
    payload = resp.json()
    cache.save(f"/fred{endpoint}", params, payload)
    return payload


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["series_id", "series_title", "obs_date", "value"])


def ingest(con) -> int:
    """Fetch all four series into raw_fred_h8. Returns rows written."""
    if not os.environ.get("FRED_API_KEY"):
        con.register("_empty", _empty_frame())
        con.execute(f'CREATE TABLE IF NOT EXISTS "{TABLE}" AS SELECT * FROM _empty')
        con.unregister("_empty")
        log.warning("FRED_API_KEY not set — created empty %s and skipped ingestion", TABLE)
        return 0

    written = 0
    with httpx.Client(base_url=BASE_URL, timeout=60) as client:
        for series_id, recorded_title in SERIES.items():
            meta = _get(client, "/series", {"series_id": series_id})
            live_title = meta["seriess"][0]["title"]
            if live_title != recorded_title:
                raise RuntimeError(
                    f"{series_id}: live title {live_title!r} != recorded {recorded_title!r} "
                    "— update docs/fred_h8_series.md deliberately before ingesting"
                )
            obs = _get(
                client,
                "/series/observations",
                {"series_id": series_id, "observation_start": OBSERVATION_START},
            )
            rows = [
                {
                    "series_id": series_id,
                    "series_title": recorded_title,
                    "obs_date": o["date"],
                    "value": o["value"],  # as served; '.' means missing — staged later
                }
                for o in obs["observations"]
            ]
            df = pd.DataFrame(rows) if rows else _empty_frame()
            written += upsert(con, TABLE, df, KEYS)
            log.info("fred %s: %d observations", series_id, len(df))
    return written


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from dotenv import load_dotenv

    load_dotenv()
    con = connect()
    try:
        ingest(con)
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

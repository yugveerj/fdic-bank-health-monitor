"""New-FDIC-quarter detector for the daily scheduled check.

Compares the latest report date the FDIC API serves (for the >$1B universe)
against the warehouse high-water mark. Prints `new_quarter=true|false` in
GitHub Actions output format. FDIC_HIGH_WATER_OVERRIDE lets the dispatch test
pretend the warehouse is behind (e.g. 20251231) to prove the trigger path
without waiting for a real quarter to land.

Usage: uv run python -m scripts.check_new_quarter
"""

from __future__ import annotations

import logging
import os
import sys

import httpx
from dotenv import load_dotenv

from ingestion.config import BASE_URL, MIN_ASSET_THOUSANDS
from ingestion.db import connect

log = logging.getLogger(__name__)


def latest_published() -> str:
    resp = httpx.get(
        f"{BASE_URL}/financials",
        params={
            "filters": f"ASSET:[{MIN_ASSET_THOUSANDS} TO *]",
            "fields": "REPDTE",
            "sort_by": "REPDTE",
            "sort_order": "DESC",
            "limit": 1,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["data"]["REPDTE"]


def warehouse_high_water() -> str:
    override = os.environ.get("FDIC_HIGH_WATER_OVERRIDE")
    if override:
        log.warning("using high-water OVERRIDE %s (dispatch test mode)", override)
        return override
    con = connect()
    try:
        return con.execute("SELECT max(REPDTE) FROM raw_fdic_financials").fetchone()[0]
    finally:
        con.close()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    published, held = latest_published(), warehouse_high_water()
    is_new = published > held
    log.info("API latest REPDTE %s vs warehouse %s -> new_quarter=%s", published, held, is_new)
    out = os.environ.get("GITHUB_OUTPUT")
    line = f"new_quarter={'true' if is_new else 'false'}"
    if out:
        with open(out, "a") as f:
            f.write(line + "\n")
            # expose the detected quarter so the workflow can name it in an alert
            f.write(f"latest_quarter={published}\n")
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())

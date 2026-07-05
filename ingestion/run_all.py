"""Full ingestion: institutions, financials, failures → BigQuery `fdic_raw`.
Idempotent — re-running upserts by key and never duplicates.
Usage: python -m ingestion.run_all"""

from __future__ import annotations

import logging

from dotenv import load_dotenv

from ingestion import fdic_failures, fdic_financials, fdic_institutions, fred_h8
from ingestion.bq import connect, max_value, row_count
from ingestion.client import FdicClient

log = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    with FdicClient() as client:
        wh = connect()
        try:
            fdic_institutions.ingest(client, wh)
            fdic_financials.ingest(client, wh)
            fdic_failures.ingest(client, wh)
            fred_h8.ingest(wh)
            for table in ("raw_fdic_institutions", "raw_fdic_financials", "raw_fdic_failures"):
                log.info("%s: %d total rows", table, row_count(wh, table))
            freshest = max_value(wh, "raw_fdic_financials", "REPDTE")
            log.info("freshest financials quarter: %s", freshest)
        finally:
            wh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

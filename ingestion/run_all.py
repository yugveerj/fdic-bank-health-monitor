"""Full ingestion: institutions, financials, failures → DuckDB. Idempotent —
re-running upserts by key and never duplicates. Usage: python -m ingestion.run_all"""

from __future__ import annotations

import logging

from dotenv import load_dotenv

from ingestion import fdic_failures, fdic_financials, fdic_institutions, fred_h8
from ingestion.client import FdicClient
from ingestion.db import connect, row_count

log = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    with FdicClient() as client:
        con = connect()
        try:
            fdic_institutions.ingest(client, con)
            fdic_financials.ingest(client, con)
            fdic_failures.ingest(client, con)
            fred_h8.ingest(con)
            for table in ("raw_fdic_institutions", "raw_fdic_financials", "raw_fdic_failures"):
                log.info("%s: %d total rows", table, row_count(con, table))
            freshest = con.execute("SELECT max(REPDTE) FROM raw_fdic_financials").fetchone()[0]
            log.info("freshest financials quarter: %s", freshest)
        finally:
            con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

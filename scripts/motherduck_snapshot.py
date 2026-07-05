"""Final MotherDuck snapshot before decommission: every table in the v1
warehouse exported to parquet and uploaded to GCS cold storage, with a
row-count manifest printed for the record. Read-only against MotherDuck —
the actual decommission (deleting the database) is a separate, deliberate
console action after this succeeds.

Env: FDIC_DB_PATH (md:fdic_bank_health), MOTHERDUCK_TOKEN, GCP_PROJECT,
GCS_ARCHIVE_BUCKET (bucket name, no gs:// prefix).

Usage: uv run python -m scripts.motherduck_snapshot
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import storage

from ingestion.db import connect

log = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    bucket_name = os.environ.get("GCS_ARCHIVE_BUCKET")
    if not bucket_name:
        raise SystemExit("GCS_ARCHIVE_BUCKET is not set")
    prefix = f"motherduck_final_{dt.datetime.now(dt.UTC).strftime('%Y%m%d')}"

    con = connect()
    client = storage.Client(project=os.environ.get("GCP_PROJECT"))
    bucket = client.bucket(bucket_name)
    manifest: list[str] = []
    try:
        tables = [r[0] for r in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY 1"
        ).fetchall()]
        if not tables:
            raise SystemExit("no tables found — wrong database?")
        with tempfile.TemporaryDirectory() as tmp:
            for table in tables:
                path = Path(tmp) / f"{table}.parquet"
                con.execute(f'COPY "{table}" TO \'{path}\' (FORMAT parquet)')
                n = con.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
                blob = bucket.blob(f"{prefix}/{table}.parquet")
                blob.upload_from_filename(str(path))
                manifest.append(f"{table}: {n} rows, {path.stat().st_size} bytes")
                log.info("archived %s (%d rows) -> gs://%s/%s/%s.parquet",
                         table, n, bucket_name, prefix, table)
        bucket.blob(f"{prefix}/MANIFEST.txt").upload_from_string(
            "\n".join(manifest) + "\n", content_type="text/plain"
        )
    finally:
        con.close()
        client.close()
    log.info("snapshot complete: %d tables under gs://%s/%s/", len(manifest), bucket_name, prefix)
    return 0


if __name__ == "__main__":
    sys.exit(main())

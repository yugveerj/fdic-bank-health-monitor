"""Load the committed fixture parquets into an ephemeral BigQuery dataset so
CI can run the full dbt project and backtest without touching the FDIC API.

Same five-bank fixture v1 loaded into a local DuckDB file. The dataset name
comes from CI_RAW_DATASET (no default, must start with ci_) so concurrent PR
runs never collide and the delete-recreate here can never touch a real
dataset. CI deletes the dataset again when the run ends (scripts/ci_cleanup).

Usage: CI_RAW_DATASET=ci_raw_<run> uv run python -m scripts.build_ci_fixture
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from google.cloud import bigquery

log = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
FIXTURES = ROOT / "tests" / "fixtures"

FRED_SCHEMA = [
    bigquery.SchemaField(name, "STRING")
    for name in ("series_id", "series_title", "obs_date", "value")
]


def ci_dataset(var: str) -> str:
    name = os.environ.get(var, "")
    if not name.startswith("ci_"):
        raise SystemExit(f"{var} must be set and start with ci_ (got {name!r})")
    return name


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    project = os.environ.get("GCP_PROJECT")
    if not project:
        raise SystemExit("GCP_PROJECT is not set — see .env.example")
    dataset = ci_dataset("CI_RAW_DATASET")

    client = bigquery.Client(project=project)
    try:
        client.delete_dataset(dataset, delete_contents=True, not_found_ok=True)
        ds = bigquery.Dataset(f"{project}.{dataset}")
        ds.location = os.environ.get("BQ_LOCATION", "US")
        client.create_dataset(ds)

        config = bigquery.LoadJobConfig(source_format=bigquery.SourceFormat.PARQUET)
        for table in ("raw_fdic_financials", "raw_fdic_institutions", "raw_fdic_failures"):
            with open(FIXTURES / f"{table}.parquet", "rb") as f:
                client.load_table_from_file(f, f"{project}.{dataset}.{table}", job_config=config
                                            ).result()
            n = client.get_table(f"{project}.{dataset}.{table}").num_rows
            log.info("%s: %d fixture rows", table, n)
        client.create_table(
            bigquery.Table(f"{project}.{dataset}.raw_fred_h8", schema=FRED_SCHEMA)
        )
    finally:
        client.close()
    log.info("CI fixture dataset %s ready", dataset)
    return 0


if __name__ == "__main__":
    sys.exit(main())

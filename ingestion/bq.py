"""BigQuery warehouse helpers: idempotent upserts via staging load + MERGE.

Replaces the DuckDB-era write path in ingestion.db (which stays in the repo for
the migration-period parity checks against the old warehouse). The contract is
identical: upsert-by-key, safe to re-run with overlapping data. BigQuery has no
transaction spanning a load job and DML, so the atomic keyed write is a load
into a staging table followed by a single MERGE.

Auth is Application Default Credentials: `gcloud auth application-default login`
locally, Workload Identity Federation in CI. Config is env-driven — see
.env.example (GCP_PROJECT required; BQ_RAW_DATASET / BQ_LOCATION optional).
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import uuid

import pandas as pd
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

log = logging.getLogger(__name__)

DEFAULT_DATASET = "fdic_raw"
# US multi-region, matching the GA4 export and bigquery-public-data (spec §2)
DEFAULT_LOCATION = "US"


class Warehouse:
    """A BigQuery client pinned to one project + dataset."""

    def __init__(self, client: bigquery.Client, dataset: str):
        self.client = client
        self.dataset = dataset

    def qualified(self, table: str) -> str:
        for part in (self.client.project, self.dataset, table):
            if "`" in part:
                raise ValueError(f"invalid identifier: {part!r}")
        return f"`{self.client.project}.{self.dataset}.{table}`"

    def close(self) -> None:
        self.client.close()


def connect() -> Warehouse:
    """Open the warehouse, creating the dataset on first use."""
    project = os.environ.get("GCP_PROJECT")
    if not project:
        raise RuntimeError("GCP_PROJECT is not set — see .env.example")
    dataset = os.environ.get("BQ_RAW_DATASET", DEFAULT_DATASET)
    location = os.environ.get("BQ_LOCATION", DEFAULT_LOCATION)
    client = bigquery.Client(project=project)
    ds = bigquery.Dataset(f"{project}.{dataset}")
    ds.location = location
    client.create_dataset(ds, exists_ok=True)
    return Warehouse(client, dataset)


def upsert(wh: Warehouse, table: str, df: pd.DataFrame, keys: list[str]) -> int:
    """Load to a staging table, then MERGE by key: safe to re-run with
    overlapping data. Creates the target from the staging schema on first
    load. Returns rows written."""
    if df.empty:
        return 0
    missing = [k for k in keys if k not in df.columns]
    if missing:
        raise ValueError(f"key column(s) {missing} not in dataframe for {table}")
    if df.duplicated(subset=keys).any():
        raise ValueError(f"duplicate keys within incoming batch for {table}")
    # MERGE matches keys with =, which never matches NULL — a null key would
    # silently insert a duplicate row on every re-run
    if df[keys].isna().any().any():
        raise ValueError(f"null key value(s) in incoming batch for {table}")

    # unique per call: a fixed name would let two concurrent runs WRITE_TRUNCATE
    # each other's batch between load and MERGE and silently swap payloads
    staging = f"_staging_{table}_{uuid.uuid4().hex[:12]}"
    try:
        _load_staging(wh, table, staging, df)
        staging_ref = wh.client.get_table(f"{wh.client.project}.{wh.dataset}.{staging}")
        # self-cleaning if the process dies before the finally: runs — orphaned
        # staging tables expire instead of accumulating
        staging_ref.expires = dt.datetime.now(dt.UTC) + dt.timedelta(hours=6)
        wh.client.update_table(staging_ref, ["expires"])
        wh.client.create_table(
            bigquery.Table(f"{wh.client.project}.{wh.dataset}.{table}", schema=staging_ref.schema),
            exists_ok=True,
        )
        columns = [f.name for f in staging_ref.schema]
        wh.client.query_and_wait(
            _merge_sql(wh.qualified(table), wh.qualified(staging), columns, keys)
        )
    finally:
        wh.client.delete_table(f"{wh.client.project}.{wh.dataset}.{staging}", not_found_ok=True)
    return len(df)


def _merge_sql(target: str, staging: str, columns: list[str], keys: list[str]) -> str:
    """The keyed-write MERGE. `target`/`staging` arrive pre-qualified."""
    on = " AND ".join(f"t.`{k}` = s.`{k}`" for k in keys)
    updates = ", ".join(f"t.`{c}` = s.`{c}`" for c in columns if c not in keys)
    col_list = ", ".join(f"`{c}`" for c in columns)
    val_list = ", ".join(f"s.`{c}`" for c in columns)
    matched = f"WHEN MATCHED THEN UPDATE SET {updates} " if updates else ""
    return (
        f"MERGE {target} t USING {staging} s ON {on} "
        f"{matched}"
        f"WHEN NOT MATCHED THEN INSERT ({col_list}) VALUES ({val_list})"
    )


def _load_staging(wh: Warehouse, table: str, staging: str, df: pd.DataFrame) -> None:
    """Truncate-load the frame into the staging table.

    If the target already exists its schema drives the load, so drift between
    runs fails loudly instead of silently forking column types. On first load
    the schema is autodetected from the frame, except all-null object columns
    (pyarrow can't type them) which are pinned to STRING — the same VARCHAR
    the DuckDB warehouse gave them."""
    config = bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE)
    try:
        config.schema = wh.client.get_table(f"{wh.client.project}.{wh.dataset}.{table}").schema
    except NotFound:
        hints = [
            bigquery.SchemaField(str(c), "STRING")
            for c in df.columns
            if df[c].dtype == object and df[c].isna().all()
        ]
        if hints:
            config.schema = hints
    job = wh.client.load_table_from_dataframe(
        df, f"{wh.client.project}.{wh.dataset}.{staging}", job_config=config
    )
    job.result()


def ensure_table(wh: Warehouse, table: str, df: pd.DataFrame) -> None:
    """Create the table (empty) from the frame's columns if it doesn't exist —
    the no-API-key path, so dbt still finds every source. Object columns map
    to STRING, matching what a real load would autodetect."""
    type_map = {
        "object": "STRING",
        "str": "STRING",
        "string": "STRING",
        "int64": "INT64",
        "Int64": "INT64",
        "float64": "FLOAT64",
        "Float64": "FLOAT64",
        "bool": "BOOL",
        "boolean": "BOOL",
    }
    schema = [
        bigquery.SchemaField(str(c), type_map.get(str(df[c].dtype), "STRING"))
        for c in df.columns
    ]
    wh.client.create_table(
        bigquery.Table(f"{wh.client.project}.{wh.dataset}.{table}", schema=schema),
        exists_ok=True,
    )


def row_count(wh: Warehouse, table: str) -> int:
    rows = wh.client.query_and_wait(f"SELECT count(*) FROM {wh.qualified(table)}")
    return next(iter(rows))[0]


def max_value(wh: Warehouse, table: str, column: str):
    rows = wh.client.query_and_wait(f"SELECT max(`{column}`) FROM {wh.qualified(table)}")
    return next(iter(rows))[0]

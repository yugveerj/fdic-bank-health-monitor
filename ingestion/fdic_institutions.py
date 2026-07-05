"""All FDIC-insured institutions, active and inactive."""

from __future__ import annotations

import logging

import pandas as pd

from ingestion.bq import upsert
from ingestion.client import FdicClient
from ingestion.config import INSTITUTION_FIELDS

log = logging.getLogger(__name__)

TABLE = "raw_fdic_institutions"
KEYS = ["CERT"]


def ingest(client: FdicClient, wh) -> int:
    rows = client.fetch_all("/institutions", fields=INSTITUTION_FIELDS, sort_by="CERT")
    df = pd.DataFrame(rows).reindex(columns=INSTITUTION_FIELDS)
    n = upsert(wh, TABLE, df, KEYS)
    log.info("institutions: %d rows", n)
    return n

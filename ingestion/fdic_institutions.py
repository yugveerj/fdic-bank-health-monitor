"""All FDIC-insured institutions, active and inactive — no ACTIVE filter, because
the backtest needs failed and merged banks present (ACTIVE=0 marks them)."""

from __future__ import annotations

import logging

import pandas as pd

from ingestion.client import FdicClient
from ingestion.config import INSTITUTION_FIELDS
from ingestion.db import upsert

log = logging.getLogger(__name__)

TABLE = "raw_fdic_institutions"
KEYS = ["CERT"]


def ingest(client: FdicClient, con) -> int:
    rows = client.fetch_all("/institutions", fields=INSTITUTION_FIELDS, sort_by="CERT")
    df = pd.DataFrame(rows).reindex(columns=INSTITUTION_FIELDS)
    n = upsert(con, TABLE, df, KEYS)
    log.info("institutions: %d rows", n)
    return n

"""All bank failure events. Small table, full pull every run.

Voluntary liquidations (e.g. Silvergate, 2023) are NOT in this endpoint —
verified live 2026-07-03. Anything relying on "every closed bank" must join
institutions.ACTIVE, not this table.
"""

from __future__ import annotations

import logging

import pandas as pd

from ingestion.client import FdicClient
from ingestion.config import FAILURE_FIELDS
from ingestion.db import upsert

log = logging.getLogger(__name__)

TABLE = "raw_fdic_failures"
KEYS = ["ID"]  # not (CERT, FAILDATE): 1930s records have NULL CERT and collide


def ingest(client: FdicClient, con) -> int:
    # sorted on CERT (the endpoint rejects sort_by=ID with a 400 — ID is a field
    # but not a sortable one); CERT is not a total order (NULL and duplicate certs
    # exist), so fetch_all's completeness guard and the ID-keyed upsert are what
    # protect against a boundary drop once this table ever exceeds one page.
    rows = client.fetch_all("/failures", fields=FAILURE_FIELDS, sort_by="CERT")
    df = pd.DataFrame(rows).reindex(columns=FAILURE_FIELDS)
    n = upsert(con, TABLE, df, KEYS)
    log.info("failures: %d rows", n)
    return n

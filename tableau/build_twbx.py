"""Package the Tableau satellite as a .twbx with embedded Hyper extracts.

Tableau Desktop Public Edition refuses to open a live-connection workbook
(extracts are required at load, not just publish — verified on 2026.1 and
2026.2), so the deliverable is the packaged form: the generated workbook XML
plus one real .hyper per datasource, zipped. The cloud named-connections stay
in the XML, which is what lets 'Keep this data in sync' refresh from the
Google Sheet after publish.

Runs in CI (WIF credentials) via the tableau-twbx workflow; the artifact is
what the owner opens and publishes. Same two queries as the Sheet export, so
the extract and the Sheet always agree.

Usage: uv run --group tableau python tableau/build_twbx.py
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery
from tableauhyperapi import (
    NULLABLE,
    Connection,
    CreateMode,
    HyperProcess,
    Inserter,
    SqlType,
    TableDefinition,
    TableName,
    Telemetry,
)

sys.path.insert(0, str(Path(__file__).parent.parent))
from reporting.tableau_sheet import fetch_frames  # noqa: E402
from tableau.build_twb import PEER_COLS, TREND_COLS, build  # noqa: E402

log = logging.getLogger(__name__)

OUT = Path(__file__).parent / "fdic_peer_satellite.twbx"

SQL_TYPES = {
    "integer": SqlType.big_int,
    "string": SqlType.text,
    "real": SqlType.double,
    "date": SqlType.date,
}


def write_hyper(path: Path, df: pd.DataFrame, cols: list) -> None:
    """One Extract.Extract table, columns typed to match the workbook's
    declared local types; NaN/NaT become NULL."""
    definition = TableDefinition(TableName("Extract", "Extract"), [
        TableDefinition.Column(name, SQL_TYPES[ltype](), NULLABLE)
        for name, _, ltype, _ in cols
    ])
    rows = []
    for record in df.itertuples(index=False):
        row = []
        for value, (_, _, ltype, _) in zip(record, cols, strict=True):
            if pd.isna(value):
                row.append(None)
            elif ltype == "date":
                row.append(pd.Timestamp(value).date())
            elif ltype == "integer":
                row.append(int(value))
            elif ltype == "real":
                row.append(float(value))
            else:
                row.append(str(value))
        rows.append(row)
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(endpoint=hyper.endpoint, database=str(path),
                        create_mode=CreateMode.CREATE_AND_REPLACE) as conn:
            conn.catalog.create_schema("Extract")
            conn.catalog.create_table(definition)
            with Inserter(conn, definition) as inserter:
                inserter.add_rows(rows)
                inserter.execute()
    log.info("wrote %s: %d rows", path.name, len(rows))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    project = os.environ.get("GCP_PROJECT")
    if not project:
        raise SystemExit("GCP_PROJECT is not set — see .env.example")
    marts = f"{project}.{os.environ.get('BQ_MARTS_DATASET', 'analytics')}"

    client = bigquery.Client(project=project)
    try:
        frames = fetch_frames(client, marts)
    finally:
        client.close()

    with tempfile.TemporaryDirectory() as tmp:
        extracts = Path(tmp) / "Data" / "Extracts"
        extracts.mkdir(parents=True)
        write_hyper(extracts / "peer_percentiles.hyper", frames["peer_percentiles"], PEER_COLS)
        write_hyper(extracts / "bank_trends.hyper", frames["bank_trends"], TREND_COLS)

        with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("fdic_peer_satellite.twb", build(extracts=True))
            for hyper in sorted(extracts.glob("*.hyper")):
                z.write(hyper, f"Data/Extracts/{hyper.name}")
    log.info("packaged %s (%.1f MB) at %s", OUT, OUT.stat().st_size / 1e6,
             dt.datetime.now(dt.UTC).isoformat(timespec="seconds"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""The idempotency guarantee everything else relies on: re-running an ingest
with overlapping data must not create duplicates or lose updates."""

import duckdb
import pandas as pd
import pytest

from ingestion.db import row_count, upsert


@pytest.fixture()
def con():
    return duckdb.connect(":memory:")


def _frame(rows):
    return pd.DataFrame(rows, columns=["cert", "repdte", "asset"])


def test_first_load_creates_table(con):
    n = upsert(con, "financials", _frame([(1, "2023-03-31", 100)]), keys=["cert", "repdte"])
    assert n == 1
    assert row_count(con, "financials") == 1


def test_rerun_same_data_no_duplicates(con):
    df = _frame([(1, "2023-03-31", 100), (2, "2023-03-31", 200)])
    upsert(con, "financials", df, keys=["cert", "repdte"])
    upsert(con, "financials", df, keys=["cert", "repdte"])
    assert row_count(con, "financials") == 2


def test_rerun_overlapping_updates_values(con):
    upsert(con, "financials", _frame([(1, "2023-03-31", 100)]), keys=["cert", "repdte"])
    upsert(con, "financials", _frame([(1, "2023-03-31", 150)]), keys=["cert", "repdte"])
    assert row_count(con, "financials") == 1
    assert con.execute("SELECT asset FROM financials").fetchone()[0] == 150


def test_duplicate_keys_in_batch_rejected(con):
    df = _frame([(1, "2023-03-31", 100), (1, "2023-03-31", 101)])
    with pytest.raises(ValueError, match="duplicate keys"):
        upsert(con, "financials", df, keys=["cert", "repdte"])


def test_missing_key_column_rejected(con):
    with pytest.raises(ValueError, match="not in dataframe"):
        upsert(con, "financials", _frame([(1, "2023-03-31", 100)]), keys=["cert", "nope"])


def test_empty_frame_is_noop(con):
    assert upsert(con, "financials", _frame([]), keys=["cert", "repdte"]) == 0

"""The BigQuery write path carries the same idempotency contract as the DuckDB
one (test_db.py): validation rejects batches that would break the re-run
guarantee, and the MERGE statement is the exact keyed write the docs promise.
Everything here runs without a GCP project — live writes are exercised by the
branch CI ingest."""

import pandas as pd
import pytest

from ingestion.bq import Warehouse, _merge_sql, upsert


def _frame(rows):
    return pd.DataFrame(rows, columns=["cert", "repdte", "asset"])


def test_empty_frame_is_noop():
    assert upsert(None, "financials", _frame([]), keys=["cert", "repdte"]) == 0


def test_missing_key_column_rejected():
    with pytest.raises(ValueError, match="not in dataframe"):
        upsert(None, "financials", _frame([(1, "2023-03-31", 100)]), keys=["cert", "nope"])


def test_duplicate_keys_in_batch_rejected():
    df = _frame([(1, "2023-03-31", 100), (1, "2023-03-31", 101)])
    with pytest.raises(ValueError, match="duplicate keys"):
        upsert(None, "financials", df, keys=["cert", "repdte"])


def test_null_key_rejected():
    # MERGE matches keys with =, which never matches NULL: a null key would
    # re-insert on every run instead of updating in place
    df = _frame([(1, None, 100)])
    with pytest.raises(ValueError, match="null key"):
        upsert(None, "financials", df, keys=["cert", "repdte"])


def test_merge_sql_updates_nonkey_columns_only():
    sql = _merge_sql("`p.d.t`", "`p.d._staging_t`", ["cert", "repdte", "asset"], ["cert", "repdte"])
    assert sql == (
        "MERGE `p.d.t` t USING `p.d._staging_t` s "
        "ON t.`cert` = s.`cert` AND t.`repdte` = s.`repdte` "
        "WHEN MATCHED THEN UPDATE SET t.`asset` = s.`asset` "
        "WHEN NOT MATCHED THEN INSERT (`cert`, `repdte`, `asset`) "
        "VALUES (s.`cert`, s.`repdte`, s.`asset`)"
    )


def test_merge_sql_all_key_columns_has_no_update_clause():
    sql = _merge_sql("`p.d.t`", "`p.d.s`", ["cert"], ["cert"])
    assert "WHEN MATCHED" not in sql
    assert "WHEN NOT MATCHED THEN INSERT (`cert`) VALUES (s.`cert`)" in sql


def test_qualified_rejects_backticks():
    class _FakeClient:
        project = "p"

    wh = Warehouse(_FakeClient(), "fdic_raw")
    assert wh.qualified("raw_fdic_financials") == "`p.fdic_raw.raw_fdic_financials`"
    with pytest.raises(ValueError, match="invalid identifier"):
        wh.qualified("bad`name")

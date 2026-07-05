"""The mart parity gate's comparison rules. Every case here is an artifact
the first live run actually produced (Timestamp-vs-date, None-vs-None flagged
as drift) or a failure the gate must never wave through. A false PASS in this
script would green-light the cutover on bad numbers."""

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from scripts.mart_parity_check import compare_mart


def _ok(result):
    return not result["problems"] and result["rows_old"] == result["rows_new"]


def test_identical_frames_pass():
    old = pd.DataFrame({"cert": [1, 2], "x": [1.0, 2.0]})
    assert _ok(compare_mart("m", old.copy(), old.copy(), ["cert"]))


def test_timestamp_vs_date_same_value_passes():
    # duckdb serves DATE as datetime64; BigQuery as datetime.date objects
    old = pd.DataFrame({"cert": [1], "d": pd.to_datetime(["1917-03-14"])})
    new = pd.DataFrame({"cert": [1], "d": [dt.date(1917, 3, 14)]})
    assert _ok(compare_mart("m", old, new, ["cert"]))


def test_null_on_both_sides_is_agreement():
    old = pd.DataFrame({"cert": [1, 2], "s": [None, "x"]})
    new = pd.DataFrame({"cert": [1, 2], "s": [np.nan, "x"]})
    assert _ok(compare_mart("m", old, new, ["cert"]))


def test_null_datetime_both_sides_passes():
    old = pd.DataFrame({"cert": [1], "d": pd.to_datetime([pd.NaT])})
    new = pd.DataFrame({"cert": [1], "d": [None]})
    assert _ok(compare_mart("m", old, new, ["cert"]))


def test_nullable_boolean_vs_none_passes():
    old = pd.DataFrame({"cert": [1, 2], "b": pd.array([None, True], dtype="boolean")})
    new = pd.DataFrame({"cert": [1, 2], "b": [None, True]})
    assert _ok(compare_mart("m", old, new, ["cert"]))


def test_real_string_difference_fails():
    old = pd.DataFrame({"cert": [1], "s": ["a"]})
    new = pd.DataFrame({"cert": [1], "s": ["b"]})
    r = compare_mart("m", old, new, ["cert"])
    assert r["problems"] and "1 cells differ" in r["problems"][0]


def test_null_vs_value_fails():
    old = pd.DataFrame({"cert": [1], "s": [None]})
    new = pd.DataFrame({"cert": [1], "s": ["x"]})
    assert compare_mart("m", old, new, ["cert"])["problems"]


def test_float_within_tolerance_passes_beyond_fails():
    old = pd.DataFrame({"cert": [1], "x": [1.0]})
    assert _ok(compare_mart("m", old.copy(), pd.DataFrame({"cert": [1], "x": [1.0 + 1e-12]}), ["cert"]))
    assert compare_mart("m", old.copy(), pd.DataFrame({"cert": [1], "x": [1.0 + 1e-6]}), ["cert"])["problems"]


def test_float_nan_both_sides_passes():
    old = pd.DataFrame({"cert": [1, 2], "x": [np.nan, 2.0]})
    assert _ok(compare_mart("m", old.copy(), old.copy(), ["cert"]))


def test_float_nan_vs_value_fails():
    old = pd.DataFrame({"cert": [1], "x": [np.nan]})
    new = pd.DataFrame({"cert": [1], "x": [1.0]})
    assert compare_mart("m", old, new, ["cert"])["problems"]


def test_worst_offender_is_reported_not_first():
    old = pd.DataFrame({"cert": [1, 2, 3], "x": [1.0, 1.0, 1.0]})
    new = pd.DataFrame({"cert": [1, 2, 3], "x": [1.0 + 1e-6, 1.0, 1.3]})
    r = compare_mart("m", old, new, ["cert"])
    assert "worst at 3" in r["problems"][0]


def test_nullable_int_vs_plain_int_passes():
    old = pd.DataFrame({"cert": [1], "n": pd.array([5], dtype="Int64")})
    new = pd.DataFrame({"cert": [1], "n": [5]})
    assert _ok(compare_mart("m", old, new, ["cert"]))


def test_key_set_difference_fails():
    old = pd.DataFrame({"cert": [1, 2], "x": [1.0, 2.0]})
    new = pd.DataFrame({"cert": [1, 3], "x": [1.0, 2.0]})
    r = compare_mart("m", old, new, ["cert"])
    assert r["problems"] and "key sets differ" in r["problems"][0]


def test_column_set_difference_fails():
    old = pd.DataFrame({"cert": [1], "x": [1.0]})
    new = pd.DataFrame({"cert": [1], "y": [1.0]})
    r = compare_mart("m", old, new, ["cert"])
    assert r["problems"] and "column sets differ" in r["problems"][0]


def test_duplicate_keys_rejected():
    old = pd.DataFrame({"cert": [1, 1], "x": [1.0, 2.0]})
    with pytest.raises(SystemExit, match="duplicate keys"):
        compare_mart("m", old.copy(), old.copy(), ["cert"])
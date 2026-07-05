"""The Sheet extract's safety rules: values must be JSON-safe for the Sheets
API (no NaN, no numpy scalars, no date objects), and the cell budget must
stop a bloated extract before it hits the Sheet's ceiling."""

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from reporting.tableau_sheet import CELL_BUDGET, as_rows, push


def test_as_rows_header_then_json_safe_values():
    df = pd.DataFrame({
        "cert": np.array([24735], dtype=np.int64),
        "report_date": [dt.date(2026, 3, 31)],
        "roa_pct": [np.float64(1.22)],
        "gap": [np.nan],
    })
    rows = as_rows(df)
    assert rows[0] == ["cert", "report_date", "roa_pct", "gap"]
    assert rows[1] == [24735, "2026-03-31", 1.22, ""]
    assert type(rows[1][0]) is int and type(rows[1][2]) is float


def test_push_refuses_oversized_extracts():
    huge = pd.DataFrame(np.zeros((CELL_BUDGET // 2, 3)))
    with pytest.raises(SystemExit, match="over the"):
        push("irrelevant", {"a": huge})

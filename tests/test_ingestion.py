
import datetime as dt

from ingestion.client import FdicClient
from ingestion.fdic_financials import quarter_ends


def test_quarter_ends_span():
    qs = quarter_ends(start="2019-03-31", today=dt.date(2020, 1, 15))
    assert qs == ["20190331", "20190630", "20190930", "20191231"]


def test_quarter_ends_excludes_future():
    qs = quarter_ends(start="2019-03-31", today=dt.date(2019, 6, 29))
    assert qs == ["20190331"]


def test_quarter_ends_format_is_undashed():
    assert all("-" not in q and len(q) == 8 for q in quarter_ends())


def test_fetch_all_paginates(monkeypatch):
    client = FdicClient(use_cache=False)
    pages = {
        0: {"meta": {"total": 5}, "data": [{"data": {"CERT": i}} for i in range(3)]},
        3: {"meta": {"total": 5}, "data": [{"data": {"CERT": i}} for i in range(3, 5)]},
    }
    calls = []

    def fake_get_json(endpoint, params):
        calls.append(params["offset"])
        return pages[params["offset"]]

    monkeypatch.setattr(client, "get_json", fake_get_json)
    rows = client.fetch_all("/institutions", fields=["CERT"], page_size=3)
    assert [r["CERT"] for r in rows] == [0, 1, 2, 3, 4]
    assert calls == [0, 3]


def test_fetch_all_raises_on_stuck_pagination(monkeypatch):
    client = FdicClient(use_cache=False)
    monkeypatch.setattr(
        client, "get_json", lambda e, p: {"meta": {"total": 10}, "data": []}
    )
    import pytest

    with pytest.raises(RuntimeError, match="empty page"):
        client.fetch_all("/institutions", fields=["CERT"], page_size=3)

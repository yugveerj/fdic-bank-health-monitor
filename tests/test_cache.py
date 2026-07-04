
from ingestion import cache


def test_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "RAW_DIR", tmp_path)
    params = {"filters": "x", "limit": 10}
    assert cache.load("/financials", params) is None
    cache.save("/financials", params, {"data": [1, 2]})
    assert cache.load("/financials", params) == {"data": [1, 2]}


def test_key_is_order_insensitive(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "RAW_DIR", tmp_path)
    a = cache.cache_path("/financials", {"a": 1, "b": 2})
    b = cache.cache_path("/financials", {"b": 2, "a": 1})
    assert a == b


def test_different_params_different_files(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "RAW_DIR", tmp_path)
    a = cache.cache_path("/financials", {"offset": 0})
    b = cache.cache_path("/financials", {"offset": 100})
    assert a != b

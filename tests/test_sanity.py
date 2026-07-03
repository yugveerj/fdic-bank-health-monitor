"""Package smoke test: entry point exists and is importable (never executed here —
running it performs a real ingestion)."""

from ingestion import run_all


def test_entry_point_shape():
    assert callable(run_all.main)

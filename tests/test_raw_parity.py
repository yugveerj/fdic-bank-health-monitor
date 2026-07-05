"""The parity gate's comparison rules: exact equality on the overlap,
BigQuery tolerated ahead of the old warehouse's high-water mark, and an empty
old side is a failure — a gate that can pass vacuously guards nothing."""

from scripts.raw_parity_check import compare


def test_matching_slices_pass():
    counts = {"20230331": 700, "20230630": 710}
    lines, ok = compare("t", counts, dict(counts))
    assert ok
    assert all("match" in line for line in lines)


def test_overlap_mismatch_fails():
    _, ok = compare("t", {"20230331": 700}, {"20230331": 699})
    assert not ok


def test_bigquery_ahead_of_high_water_tolerated():
    lines, ok = compare("t", {"20230331": 700}, {"20230331": 700, "20230630": 710})
    assert ok
    assert any("bigquery ahead" in line for line in lines)


def test_missing_from_bigquery_fails():
    _, ok = compare("t", {"20230331": 700, "20230630": 710}, {"20230630": 710})
    assert not ok


def test_bigquery_only_slice_below_high_water_fails():
    # a gap in the middle is missing data, not fresher data
    _, ok = compare("t", {"20230630": 710}, {"20230331": 700, "20230630": 710})
    assert not ok


def test_empty_old_side_fails():
    lines, ok = compare("t", {}, {"20230331": 700})
    assert not ok
    assert "old warehouse empty" in lines[0]

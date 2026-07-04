"""The 2023 backtest results are frozen (CLAUDE.md standing rule): SVB 1/35,
Signature 2/35, Silvergate 2/128, First Republic 8/35, Republic 86/826.

This pins the committed exhibit so a regenerated backtest with different numbers
fails CI even on pull requests, where the production warehouse isn't available.
The live computation is guarded separately by run_backtest.assert_frozen_ranks.
"""

import csv
from pathlib import Path

LABELED_CSV = Path(__file__).parent.parent / "docs" / "backtest" / "labeled_banks.csv"

# cert -> (peer_band, rank_in_band, band_size, rank_overall, n_overall) as CSV text
FROZEN = {
    "27330": ("$10B-$100B", "2", "128", "8", "989"),
    "24735": (">$100B", "1", "35", "26", "989"),
    "57053": (">$100B", "2", "35", "60", "989"),
    "59017": (">$100B", "8", "35", "355", "989"),
    "27332": ("$1B-$10B", "86", "826", "95", "989"),
}


def test_labeled_bank_ranks_are_frozen():
    rows = {r["cert"]: r for r in csv.DictReader(LABELED_CSV.open())}
    missing = set(FROZEN) - set(rows)
    assert not missing, f"labeled exhibit is missing frozen certs: {missing}"
    for cert, expected in FROZEN.items():
        r = rows[cert]
        got = (r["peer_band"], r["rank_in_band"], r["band_size"], r["rank_overall"], r["n_overall"])
        assert got == expected, f"frozen ranks changed for cert {cert}: got {got}, expected {expected}"

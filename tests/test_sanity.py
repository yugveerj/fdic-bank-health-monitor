"""Hello-world test: proves the CI test path works end to end before real code exists."""

from ingestion import run_all


def test_run_all_entry_point_exists():
    assert run_all.main() == 0

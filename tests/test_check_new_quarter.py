"""The daily-cron new-quarter detector decides whether the pipeline re-ingests.
Its trigger comparison and the GitHub Actions output write were untested."""

from scripts import check_new_quarter as cnq


def _run(monkeypatch, capsys, published, held):
    monkeypatch.setattr(cnq, "latest_published", lambda: published)
    monkeypatch.setattr(cnq, "warehouse_high_water", lambda: held)
    rc = cnq.main()
    return rc, capsys.readouterr().out


def test_new_quarter_detected(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    rc, out = _run(monkeypatch, capsys, "20240331", "20231231")
    assert rc == 0
    assert "new_quarter=true" in out


def test_same_quarter_is_not_new(monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    _, out = _run(monkeypatch, capsys, "20231231", "20231231")
    assert "new_quarter=false" in out


def test_warehouse_ahead_is_not_new(monkeypatch, capsys):
    # a lexicographic comparison is only safe on fixed-width YYYYMMDD; guard it
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    _, out = _run(monkeypatch, capsys, "20230930", "20231231")
    assert "new_quarter=false" in out


def test_writes_github_output(monkeypatch, capsys, tmp_path):
    gh_out = tmp_path / "gh_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(gh_out))
    _run(monkeypatch, capsys, "20240331", "20231231")
    written = gh_out.read_text()
    assert "new_quarter=true" in written
    # the detected quarter is exposed so the workflow can name it in the alert
    assert "latest_quarter=20240331" in written


def test_high_water_override_short_circuits_the_warehouse(monkeypatch):
    monkeypatch.setenv("FDIC_HIGH_WATER_OVERRIDE", "20251231")
    # returns the override without connecting to the warehouse (the dispatch-test path)
    assert cnq.warehouse_high_water() == "20251231"

"""The 2023 backtest, reproducible from one command:

    uv run python -m scripts.run_backtest

What it does, in order:
1. Builds a physically frozen warehouse: copies raw tables into backtest.duckdb
   with financials truncated at the as-of date, then runs the full dbt project
   against it (dbt --vars as_of also filters in-model, belt and braces).
2. Proves the freeze is real: the frozen build's composite scores at the as-of
   quarter must match the production mart's rows exactly — demonstrating that
   every screen metric uses only backward-looking data.
3. Emits the exhibits to docs/backtest/: the full ranked table, the labeled
   banks' ranks and percentiles (overall and within band), and a top-decile
   false-positive sample for the written analysis.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import duckdb

log = logging.getLogger(__name__)

AS_OF = "2022-06-30"
ROOT = Path(__file__).parent.parent
# both paths are env-overridable so CI can run the whole thing on the fixture
BACKTEST_DB = Path(os.environ.get("BACKTEST_DB_PATH", ROOT / "backtest.duckdb")).resolve()
PROD_DB = Path(os.environ.get("FDIC_PROD_DB", ROOT / "warehouse.duckdb")).resolve()
OUT_DIR = Path(os.environ.get("BACKTEST_OUT_DIR", ROOT / "docs" / "backtest")).resolve()

# The 2023 label set: three failures + one voluntary liquidation.
# Republic Bank (27332, failed 2024) is reported as an out-of-window check.
LABELED = {24735: "failed", 57053: "failed", 59017: "failed", 27330: "liquidated"}
OUT_OF_WINDOW = {27332: "failed_2024"}

# Published, FROZEN backtest ranks at the 2022-06-30 freeze (CLAUDE.md standing
# rule: these never change silently). Asserted on every canonical production run
# (see assert_frozen_ranks). cert -> (peer_band, rank_in_band, band_size, rank_overall).
FROZEN_RANKS = {
    27330: ("$10B-$100B", 2, 128, 8),
    24735: (">$100B", 1, 35, 26),
    57053: (">$100B", 2, 35, 60),
    59017: (">$100B", 8, 35, 355),
    27332: ("$1B-$10B", 86, 826, 95),
}
FROZEN_N_OVERALL = 989


def build_frozen_warehouse() -> None:
    BACKTEST_DB.unlink(missing_ok=True)
    con = duckdb.connect(str(BACKTEST_DB))
    try:
        con.execute(f"ATTACH '{PROD_DB}' AS prod (READ_ONLY)")
        # copy every raw table generically so a new source can never silently
        # break the frozen build again; time-bounded ones get truncated at as-of
        raw_tables = [r[0] for r in con.execute(
            "SELECT table_name FROM duckdb_tables() WHERE database_name='prod' AND table_name LIKE 'raw_%'"
        ).fetchall()]
        for table in raw_tables:
            if table == "raw_fdic_financials":
                con.execute(
                    f"""CREATE TABLE {table} AS SELECT * FROM prod.{table}
                        WHERE strptime(REPDTE, '%Y%m%d')::date <= DATE '{AS_OF}'"""
                )
            elif table == "raw_fred_h8":
                con.execute(
                    f"CREATE TABLE {table} AS SELECT * FROM prod.{table} WHERE obs_date <= '{AS_OF}'"
                )
            else:
                con.execute(f"CREATE TABLE {table} AS SELECT * FROM prod.{table}")
        n = con.execute("SELECT count(*), max(REPDTE) FROM raw_fdic_financials").fetchone()
        log.info("frozen raw financials: %d rows, max REPDTE %s", n[0], n[1])
    finally:
        con.close()

    result = subprocess.run(
        ["uv", "run", "dbt", "build", "--vars", f"{{as_of: '{AS_OF}'}}"],
        cwd=ROOT / "dbt",
        env={"DBT_PROFILES_DIR": ".", "DBT_TARGET": "backtest", "PATH": __import__("os").environ["PATH"],
             "HOME": __import__("os").environ["HOME"],
             "BACKTEST_DB_PATH": str(BACKTEST_DB)},
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error("dbt build failed:\n%s", result.stdout[-3000:])
        raise SystemExit(1)
    log.info("frozen dbt build green")


def prove_equivalence() -> None:
    """Frozen composite at the as-of quarter must equal production's rows exactly."""
    con = duckdb.connect(str(BACKTEST_DB), read_only=True)
    try:
        con.execute(f"ATTACH '{PROD_DB}' AS prod (READ_ONLY)")
        diff = con.execute(
            f"""
            WITH frozen AS (
                SELECT cert, peer_band, round(composite_score, 10) AS s, n_screen_metrics
                FROM main.mart_outlier_flags WHERE report_date = DATE '{AS_OF}'
            ),
            production AS (
                SELECT cert, peer_band, round(composite_score, 10) AS s, n_screen_metrics
                FROM prod.main.mart_outlier_flags WHERE report_date = DATE '{AS_OF}'
            )
            SELECT count(*) FROM (
                SELECT * FROM frozen EXCEPT SELECT * FROM production
                UNION ALL
                SELECT * FROM production EXCEPT SELECT * FROM frozen
            )
            """
        ).fetchone()[0]
        counts = con.execute(
            f"""SELECT (SELECT count(*) FROM main.mart_outlier_flags WHERE report_date = DATE '{AS_OF}'),
                       (SELECT count(*) FROM prod.main.mart_outlier_flags WHERE report_date = DATE '{AS_OF}')"""
        ).fetchone()
        if diff != 0 or counts[0] != counts[1]:
            log.error("EQUIVALENCE FAILED: %d mismatched rows (frozen %d vs prod %d)", diff, *counts)
            raise SystemExit(1)
        log.info(
            "equivalence proven: %d bank composites identical between the physically "
            "frozen build and the production mart at %s — the screen uses only "
            "backward-looking data", counts[0], AS_OF,
        )
    finally:
        con.close()


def emit_exhibits() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(BACKTEST_DB), read_only=True)
    try:
        base = f"""
            SELECT
                o.cert,
                b.bank_name,
                o.peer_band,
                o.composite_score,
                o.n_screen_metrics,
                o.z_uninsured_share, o.z_brokered_share, o.z_securities_share,
                o.z_asset_growth_3y, o.z_nim_trend, o.z_equity_ratio,
                f.likely_merger_quarter,
                rank() OVER (PARTITION BY o.peer_band ORDER BY o.composite_score DESC) AS rank_in_band,
                count(*)  OVER (PARTITION BY o.peer_band) AS band_size,
                percent_rank() OVER (PARTITION BY o.peer_band ORDER BY o.composite_score) AS pctile_in_band,
                rank() OVER (ORDER BY o.composite_score DESC) AS rank_overall,
                count(*)  OVER () AS n_overall,
                percent_rank() OVER (ORDER BY o.composite_score) AS pctile_overall
            FROM main.mart_outlier_flags o
            JOIN main.dim_banks b USING (cert)
            LEFT JOIN main.fct_bank_quarters f
                   ON f.cert = o.cert AND f.report_date = o.report_date
            WHERE o.report_date = DATE '{AS_OF}'
        """
        con.execute(f"COPY ({base} ORDER BY composite_score DESC) TO '{OUT_DIR}/ranked_full.csv' (HEADER)")

        labeled_ids = ",".join(str(c) for c in (*LABELED, *OUT_OF_WINDOW))
        con.execute(
            f"""COPY (SELECT *, CASE WHEN cert IN ({",".join(map(str, LABELED))}) THEN '2023 label set'
                                     ELSE 'out of window (2024)' END AS label_group
                      FROM ({base}) WHERE cert IN ({labeled_ids})
                      ORDER BY composite_score DESC)
                TO '{OUT_DIR}/labeled_banks.csv' (HEADER)"""
        )

        con.execute(
            f"""COPY (SELECT * FROM ({base})
                      WHERE pctile_in_band >= 0.9
                        AND cert NOT IN ({labeled_ids})
                      ORDER BY composite_score DESC LIMIT 12)
                TO '{OUT_DIR}/false_positive_sample.csv' (HEADER)"""
        )

        summary = con.execute(
            f"SELECT bank_name, peer_band, rank_in_band, band_size, "
            f"round(pctile_in_band*100,1), rank_overall, n_overall, round(pctile_overall*100,1) "
            f"FROM ({base}) WHERE cert IN ({labeled_ids}) ORDER BY composite_score DESC"
        ).fetchall()
        log.info("labeled banks at the %s freeze:", AS_OF)
        for r in summary:
            log.info(
                "  %-22s %-11s band %d/%d (pctile %.1f)  overall %d/%d (pctile %.1f)",
                r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7],
            )
        log.info("exhibits written to %s", OUT_DIR)
    finally:
        con.close()


def assert_frozen_ranks() -> None:
    """The labeled banks' ranks must match the published frozen values.

    prove_equivalence only shows the frozen build agrees with production; it cannot
    catch a change to the composite formula, the metric set, or the sign directions,
    because both sides move together. This pins the actual output numbers. Skipped
    when FDIC_PROD_DB is overridden (the CI fixture or an alternate warehouse), where
    the universe — and therefore the ranks — legitimately differ.
    """
    if os.environ.get("FDIC_PROD_DB"):
        log.info("frozen-rank assertion skipped: FDIC_PROD_DB overrides the production warehouse")
        return
    con = duckdb.connect(str(BACKTEST_DB), read_only=True)
    try:
        rows = con.execute(
            f"""
            WITH ranked AS (
                SELECT cert, peer_band,
                    rank()   OVER (PARTITION BY peer_band ORDER BY composite_score DESC) AS rank_in_band,
                    count(*) OVER (PARTITION BY peer_band) AS band_size,
                    rank()   OVER (ORDER BY composite_score DESC) AS rank_overall,
                    count(*) OVER () AS n_overall
                FROM main.mart_outlier_flags WHERE report_date = DATE '{AS_OF}'
            )
            SELECT cert, peer_band, rank_in_band, band_size, rank_overall, n_overall
            FROM ranked WHERE cert IN ({",".join(str(c) for c in FROZEN_RANKS)})
            """
        ).fetchall()
        found = {r[0]: r[1:] for r in rows}
        problems = []
        for cert, expected in FROZEN_RANKS.items():
            if cert not in found:
                problems.append(f"cert {cert} absent from the frozen composite")
                continue
            band, rib, bsize, roverall, n_overall = found[cert]
            if (band, rib, bsize, roverall) != expected or n_overall != FROZEN_N_OVERALL:
                problems.append(
                    f"cert {cert}: got {band} {rib}/{bsize} overall {roverall}/{n_overall}; "
                    f"expected {expected[0]} {expected[1]}/{expected[2]} overall {expected[3]}/{FROZEN_N_OVERALL}"
                )
        if problems:
            log.error("FROZEN RANKS CHANGED — the published backtest results moved:\n  %s",
                      "\n  ".join(problems))
            raise SystemExit(1)
        log.info("frozen ranks verified: all %d labeled banks match the published values", len(FROZEN_RANKS))
    finally:
        con.close()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not PROD_DB.exists():
        log.error("production warehouse missing — run ingestion and dbt build first")
        return 1
    build_frozen_warehouse()
    prove_equivalence()
    emit_exhibits()
    assert_frozen_ranks()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""The 2023 backtest on BigQuery, reproducible from one command:

    uv run python -m scripts.run_backtest

What it does, in order:
1. Builds a physically frozen warehouse: copies the raw tables into their own
   dataset with financials truncated at the as-of date, then runs the full dbt
   project against it (dbt --vars as_of also filters in-model, belt and braces).
2. Proves the freeze is real: the frozen build's composite scores at the as-of
   quarter must match the production mart's rows exactly — demonstrating that
   every screen metric uses only backward-looking data.
3. Emits the exhibits to docs/backtest/: the full ranked table, the labeled
   banks' ranks and percentiles (overall and within band), and a top-decile
   false-positive sample for the written analysis.

Datasets (all env-overridable): frozen raw copies land in `backtest_raw`, the
frozen models build into `dbt_backtest` (the profiles.yml backtest target),
and the equivalence proof compares against FDIC_PROD_DATASET (default
`analytics`). The two backtest datasets are recreated from scratch each run —
the BigQuery equivalent of v1 deleting backtest.duckdb — and the script
refuses to treat any real dataset as scratch.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from google.cloud import bigquery

log = logging.getLogger(__name__)

AS_OF = "2022-06-30"
ROOT = Path(__file__).parent.parent
OUT_DIR = Path(os.environ.get("BACKTEST_OUT_DIR", ROOT / "docs" / "backtest")).resolve()

# The 2023 label set: three failures + one voluntary liquidation.
# Republic Bank (27332, failed 2024) is reported as an out-of-window check.
LABELED = {24735: "failed", 57053: "failed", 59017: "failed", 27330: "liquidated"}
OUT_OF_WINDOW = {27332: "failed_2024"}

# Published, FROZEN backtest ranks at the 2022-06-30 freeze (CLAUDE.md standing
# rule: these never change silently). Asserted on every canonical production run
# (see assert_ranks). cert -> (peer_band, rank_in_band, band_size, rank_overall).
FROZEN_RANKS = {
    27330: ("$10B-$100B", 2, 128, 8),
    24735: (">$100B", 1, 35, 26),
    57053: (">$100B", 2, 35, 60),
    59017: (">$100B", 8, 35, 355),
    27332: ("$1B-$10B", 86, 826, 95),
}
FROZEN_N_OVERALL = 989

# The CI fixture's own golden ranks (not a published number). Only SVB among the
# labeled banks is in the fixture's institutions/financials; its three peer bands
# hold five real banks each, so this pins the median/MAD/winsorization/ranking
# math end to end on every fixture backtest. Update these if the fixture changes.
FIXTURE_RANKS = {24735: (">$100B", 1, 5, 1)}
FIXTURE_N_OVERALL = 15


def _env() -> dict:
    project = os.environ.get("GCP_PROJECT")
    if not project:
        raise SystemExit("GCP_PROJECT is not set — see .env.example")
    cfg = {
        "project": project,
        "raw": os.environ.get("BQ_RAW_DATASET", "fdic_raw"),
        "frozen_raw": os.environ.get("BACKTEST_RAW_DATASET", "backtest_raw"),
        "models": os.environ.get("BACKTEST_DATASET", "dbt_backtest"),
        "prod": os.environ.get("FDIC_PROD_DATASET", "analytics"),
    }
    # the two scratch datasets get wiped every run — never let them alias a
    # real one (this is the only delete this project performs)
    protected = {cfg["raw"], cfg["prod"], "fdic_raw", "analytics", "dbt_dev"}
    for scratch in (cfg["frozen_raw"], cfg["models"]):
        if scratch in protected:
            raise SystemExit(f"refusing to use protected dataset {scratch!r} as backtest scratch")
    return cfg


def _q(client: bigquery.Client, sql: str):
    return client.query_and_wait(sql)


def build_frozen_warehouse(client: bigquery.Client, cfg: dict) -> None:
    for scratch in (cfg["frozen_raw"], cfg["models"]):
        client.delete_dataset(scratch, delete_contents=True, not_found_ok=True)
        ds = bigquery.Dataset(f"{cfg['project']}.{scratch}")
        ds.location = os.environ.get("BQ_LOCATION", "US")
        client.create_dataset(ds)

    # copy every raw table generically so a new source can never silently
    # break the frozen build again; time-bounded ones get truncated at as-of
    raw_tables = [
        t.table_id for t in client.list_tables(cfg["raw"]) if t.table_id.startswith("raw_")
    ]
    for table in raw_tables:
        src = f"`{cfg['project']}.{cfg['raw']}.{table}`"
        dst = f"`{cfg['project']}.{cfg['frozen_raw']}.{table}`"
        if table == "raw_fdic_financials":
            _q(client, f"""CREATE TABLE {dst} AS SELECT * FROM {src}
                           WHERE parse_date('%Y%m%d', REPDTE) <= DATE '{AS_OF}'""")
        elif table == "raw_fred_h8":
            _q(client, f"CREATE TABLE {dst} AS SELECT * FROM {src} WHERE obs_date <= '{AS_OF}'")
        else:
            _q(client, f"CREATE TABLE {dst} AS SELECT * FROM {src}")
    n = next(iter(_q(client, f"""SELECT count(*), max(REPDTE)
                                 FROM `{cfg['project']}.{cfg['frozen_raw']}.raw_fdic_financials`""")))
    log.info("frozen raw financials: %d rows, max REPDTE %s", n[0], n[1])

    result = subprocess.run(
        ["uv", "run", "dbt", "build", "--vars", f"{{as_of: '{AS_OF}'}}"],
        cwd=ROOT / "dbt",
        env={
            **os.environ,
            "DBT_PROFILES_DIR": ".",
            "DBT_TARGET": "backtest",
            "BQ_RAW_DATASET": cfg["frozen_raw"],
            "BACKTEST_DATASET": cfg["models"],
        },
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log.error("dbt build failed:\n%s", result.stdout[-3000:])
        raise SystemExit(1)
    log.info("frozen dbt build green")


def prove_equivalence(client: bigquery.Client, cfg: dict) -> None:
    """Frozen composite at the as-of quarter must equal production's rows exactly."""
    frozen = f"`{cfg['project']}.{cfg['models']}.mart_outlier_flags`"
    prod = f"`{cfg['project']}.{cfg['prod']}.mart_outlier_flags`"
    diff = next(iter(_q(client, f"""
        WITH frozen AS (
            SELECT cert, peer_band, round(composite_score, 10) AS s, n_screen_metrics
            FROM {frozen} WHERE report_date = DATE '{AS_OF}'
        ),
        production AS (
            SELECT cert, peer_band, round(composite_score, 10) AS s, n_screen_metrics
            FROM {prod} WHERE report_date = DATE '{AS_OF}'
        )
        SELECT count(*) FROM (
            (SELECT * FROM frozen EXCEPT DISTINCT SELECT * FROM production)
            UNION ALL
            (SELECT * FROM production EXCEPT DISTINCT SELECT * FROM frozen)
        )
        """)))[0]
    counts = next(iter(_q(client, f"""
        SELECT (SELECT count(*) FROM {frozen} WHERE report_date = DATE '{AS_OF}'),
               (SELECT count(*) FROM {prod} WHERE report_date = DATE '{AS_OF}')""")))
    if diff != 0 or counts[0] != counts[1]:
        log.error("EQUIVALENCE FAILED: %d mismatched rows (frozen %d vs prod %d)", diff, *counts)
        raise SystemExit(1)
    log.info(
        "equivalence proven: %d bank composites identical between the physically "
        "frozen build and the production mart at %s — the screen uses only "
        "backward-looking data", counts[0], AS_OF,
    )


def _base_query(cfg: dict) -> str:
    d = f"{cfg['project']}.{cfg['models']}"
    return f"""
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
        FROM `{d}.mart_outlier_flags` o
        JOIN `{d}.dim_banks` b USING (cert)
        LEFT JOIN `{d}.fct_bank_quarters` f
               ON f.cert = o.cert AND f.report_date = o.report_date
        WHERE o.report_date = DATE '{AS_OF}'
    """


def _write_csv(client: bigquery.Client, sql: str, path: Path) -> None:
    df = _q(client, sql).to_dataframe()
    # DuckDB's COPY wrote booleans lowercase; keep the committed exhibits diffable
    for col in df.columns:
        if df[col].dtype == bool or str(df[col].dtype) == "boolean":
            df[col] = df[col].map({True: "true", False: "false"})
    df.to_csv(path, index=False)


def emit_exhibits(client: bigquery.Client, cfg: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = _base_query(cfg)
    labeled_ids = ",".join(str(c) for c in (*LABELED, *OUT_OF_WINDOW))

    _write_csv(client, f"SELECT * FROM ({base}) ORDER BY composite_score DESC",
               OUT_DIR / "ranked_full.csv")
    _write_csv(
        client,
        f"""SELECT *, CASE WHEN cert IN ({",".join(map(str, LABELED))}) THEN '2023 label set'
                           ELSE 'out of window (2024)' END AS label_group
            FROM ({base}) WHERE cert IN ({labeled_ids})
            ORDER BY composite_score DESC""",
        OUT_DIR / "labeled_banks.csv",
    )
    _write_csv(
        client,
        f"""SELECT * FROM ({base})
            WHERE pctile_in_band >= 0.9 AND cert NOT IN ({labeled_ids})
            ORDER BY composite_score DESC LIMIT 12""",
        OUT_DIR / "false_positive_sample.csv",
    )

    summary = list(_q(client, f"""
        SELECT bank_name, peer_band, rank_in_band, band_size,
               round(pctile_in_band*100,1), rank_overall, n_overall, round(pctile_overall*100,1)
        FROM ({base}) WHERE cert IN ({labeled_ids}) ORDER BY composite_score DESC"""))
    log.info("labeled banks at the %s freeze:", AS_OF)
    for r in summary:
        log.info(
            "  %-22s %-11s band %d/%d (pctile %.1f)  overall %d/%d (pctile %.1f)",
            r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7],
        )
    log.info("exhibits written to %s", OUT_DIR)


def _assert_ranks(client: bigquery.Client, cfg: dict, expected: dict,
                  n_overall_expected: int, context: str) -> None:
    rows = list(_q(client, f"""
        WITH ranked AS (
            SELECT cert, peer_band,
                rank()   OVER (PARTITION BY peer_band ORDER BY composite_score DESC) AS rank_in_band,
                count(*) OVER (PARTITION BY peer_band) AS band_size,
                rank()   OVER (ORDER BY composite_score DESC) AS rank_overall,
                count(*) OVER () AS n_overall
            FROM `{cfg['project']}.{cfg['models']}.mart_outlier_flags`
            WHERE report_date = DATE '{AS_OF}'
        )
        SELECT cert, peer_band, rank_in_band, band_size, rank_overall, n_overall
        FROM ranked WHERE cert IN ({",".join(str(c) for c in expected)})
        """))
    found = {r[0]: tuple(r)[1:] for r in rows}
    problems = []
    for cert, exp in expected.items():
        if cert not in found:
            problems.append(f"cert {cert} absent from the composite")
            continue
        band, rib, bsize, roverall, n_overall = found[cert]
        if (band, rib, bsize, roverall) != exp or n_overall != n_overall_expected:
            problems.append(
                f"cert {cert}: got {band} {rib}/{bsize} overall {roverall}/{n_overall}; "
                f"expected {exp[0]} {exp[1]}/{exp[2]} overall {exp[3]}/{n_overall_expected}"
            )
    if problems:
        log.error("%s RANKS CHANGED:\n  %s", context.upper(), "\n  ".join(problems))
        raise SystemExit(1)
    log.info("%s ranks verified: all %d labeled banks match", context, len(expected))


def assert_ranks(client: bigquery.Client, cfg: dict) -> None:
    """Pin the labeled banks' ranks so a regression in the composite, the metric set,
    the sign directions, or the median/MAD/winsorization/ranking math fails loudly —
    something prove_equivalence cannot catch, since it moves the frozen build and
    production together. BACKTEST_RANK_SET selects the golden values: `frozen`
    (default — the published production ranks), `fixture` (the CI fixture's own),
    or `skip` for runs against a deliberately nonstandard raw dataset.
    """
    mode = os.environ.get("BACKTEST_RANK_SET", "frozen")
    if mode == "fixture":
        _assert_ranks(client, cfg, FIXTURE_RANKS, FIXTURE_N_OVERALL, "fixture")
    elif mode == "skip":
        log.info("rank assertion skipped: BACKTEST_RANK_SET=skip")
    else:
        _assert_ranks(client, cfg, FROZEN_RANKS, FROZEN_N_OVERALL, "frozen production")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from dotenv import load_dotenv

    load_dotenv()
    cfg = _env()
    client = bigquery.Client(project=cfg["project"])
    try:
        tables = {t.table_id for t in client.list_tables(cfg["prod"])}
        if "mart_outlier_flags" not in tables:
            log.error("no marts in dataset %s — run dbt build first", cfg["prod"])
            return 1
        build_frozen_warehouse(client, cfg)
        prove_equivalence(client, cfg)
        emit_exhibits(client, cfg)
        assert_ranks(client, cfg)
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Weekly sector forecasts from the FRED H.8 aggregates: 12 weeks ahead with
95% intervals, method chosen per series by rolling-origin backtest against a
seasonal-naive baseline (forecasting/methods.py). Writes two tables beside
the marts, both rebuilt on every run:

- mart_h8_forecasts          the published forecast paths
- mart_h8_forecast_backtest  MAPE/sMAPE per series and method, published flag

Neutrality is structural, not a convention: the input allowlist is the four
sector-level aggregates from ingestion.fred_h8.SERIES, verified against what
the staging view actually serves — bank-level forecasting is prohibited
(CLAUDE.md) and this module has no path to a bank-level series.

Usage: uv run python -m forecasting.h8_forecast
"""

from __future__ import annotations

import logging
import os
import sys

import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery

from forecasting import methods
from ingestion.fred_h8 import SERIES

log = logging.getLogger(__name__)


def weekly_series(df: pd.DataFrame, series_id: str) -> pd.Series:
    """One clean weekly series, or a loud failure. The staging view drops
    FRED's '.' placeholders; a hole in the weekly grid would silently break
    lag-52 alignment, so a gap stops the run rather than getting imputed —
    never fabricate data, including for model input."""
    sub = df[df["series_id"] == series_id].sort_values("obs_date")
    dates = pd.to_datetime(sub["obs_date"])
    gaps = dates.diff().dropna().dt.days
    if not (gaps == 7).all():
        bad = dates[1:][gaps != 7].dt.date.tolist()[:3]
        raise SystemExit(f"{series_id}: weekly grid has gaps near {bad} — investigate, don't impute")
    return pd.Series(sub["value_billions"].to_numpy(), index=dates.to_numpy())


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_dotenv()
    project = os.environ.get("GCP_PROJECT")
    if not project:
        raise SystemExit("GCP_PROJECT is not set — see .env.example")
    marts = f"{project}.{os.environ.get('BQ_MARTS_DATASET', 'analytics')}"

    client = bigquery.Client(project=project)
    try:
        df = client.query_and_wait(
            f"SELECT series_id, series_title, obs_date, value_billions "
            f"FROM `{marts}.stg_fred__h8` ORDER BY obs_date"
        ).to_dataframe()
        served = set(df["series_id"].unique())
        if served != set(SERIES):
            raise SystemExit(
                f"series mismatch: staging serves {sorted(served)}, "
                f"allowlist is {sorted(SERIES)} — sector-level aggregates only"
            )

        forecast_rows, score_rows = [], []
        for series_id, title in SERIES.items():
            y = weekly_series(df, series_id)
            scores = methods.evaluate(y)
            chosen = methods.select_method(scores)
            log.info("%s: %s", series_id, ", ".join(
                f"{r.method} sMAPE {r.smape:.3f}%" for r in scores.itertuples()))
            log.info("%s: publishing %s%s", series_id, chosen,
                     "" if chosen != methods.BASELINE else " (no candidate beat the baseline)")

            path = methods.forecast_with_intervals(y, chosen)
            trained_through = y.index[-1]
            for r in path.itertuples():
                forecast_rows.append({
                    "series_id": series_id,
                    "series_title": title,
                    "forecast_week": (trained_through + pd.Timedelta(weeks=r.step)).date(),
                    "horizon_weeks": int(r.step),
                    "forecast": float(r.forecast),
                    "lo_95": float(r.lo_95),
                    "hi_95": float(r.hi_95),
                    "method": chosen,
                    "trained_through": trained_through.date(),
                })
            for r in scores.itertuples():
                score_rows.append({
                    "series_id": series_id,
                    "series_title": title,
                    "method": r.method,
                    "mape": float(r.mape),
                    "smape": float(r.smape),
                    "n_origins": int(r.n_origins),
                    "published": r.method == chosen,
                })

        stamp = pd.Timestamp.now(tz="UTC")
        for name, rows in (("mart_h8_forecasts", forecast_rows),
                           ("mart_h8_forecast_backtest", score_rows)):
            out = pd.DataFrame(rows)
            out["generated_at"] = stamp
            client.load_table_from_dataframe(
                out, f"{marts}.{name}",
                job_config=bigquery.LoadJobConfig(
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
                ),
            ).result()
            log.info("wrote %s.%s: %d rows", marts, name, len(out))
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

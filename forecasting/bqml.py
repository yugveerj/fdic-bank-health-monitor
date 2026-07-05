"""BigQuery ML ARIMA_PLUS as a third forecasting candidate, held to exactly
the same rolling-origin protocol as the statsmodels methods: same origins
(shared constants from forecasting.methods), same expanding window, same
horizon, same pooled MAPE/sMAPE — one honest table, whichever method wins.

Models live in the `ml` dataset (env BQ_ML_DATASET): one scratch model per
series reused across backtest origins, and a full-history model per series
whose ML.FORECAST ships if ARIMA_PLUS wins that series' backtest.
"""

from __future__ import annotations

import logging

import pandas as pd
from google.cloud import bigquery

from forecasting.methods import HORIZON, MIN_TRAIN, STEP, mape, smape

log = logging.getLogger(__name__)

METHOD = "bqml_arima_plus"


def _train_sql(model: str, marts: str, series_id: str, n_rows: int | None) -> str:
    limit = f"WHERE rn <= {n_rows}" if n_rows is not None else ""
    return f"""
        CREATE OR REPLACE MODEL `{model}`
        OPTIONS (
          model_type = 'ARIMA_PLUS',
          time_series_timestamp_col = 'obs_date',
          time_series_data_col = 'value_billions',
          horizon = {HORIZON},
          data_frequency = 'WEEKLY'
        ) AS
        SELECT obs_date, value_billions
        FROM (
          SELECT obs_date, value_billions,
                 ROW_NUMBER() OVER (ORDER BY obs_date) AS rn
          FROM `{marts}.stg_fred__h8`
          WHERE series_id = '{series_id}'
        )
        {limit}"""


def _forecast_rows(client: bigquery.Client, model: str) -> list[tuple]:
    rows = client.query_and_wait(f"""
        SELECT CAST(forecast_timestamp AS DATE), forecast_value,
               prediction_interval_lower_bound, prediction_interval_upper_bound
        FROM ML.FORECAST(MODEL `{model}`, STRUCT({HORIZON} AS horizon, 0.95 AS confidence_level))
        ORDER BY forecast_timestamp""")
    out = [tuple(r) for r in rows]
    if len(out) != HORIZON:
        raise SystemExit(f"{model}: ML.FORECAST returned {len(out)} steps, expected {HORIZON}")
    return out


def backtest(client: bigquery.Client, marts: str, ml_dataset: str,
             series_id: str, y: pd.Series) -> dict:
    """One scores row, protocol-identical to methods.rolling_origin_backtest:
    train on the first `origin` observations, forecast HORIZON, pool errors."""
    model = f"{ml_dataset}.arima_bt_{series_id.lower()}"
    actuals, forecasts = [], []
    origins = range(MIN_TRAIN, len(y) - HORIZON + 1, STEP)
    for origin in origins:
        client.query_and_wait(_train_sql(model, marts, series_id, origin))
        fc = _forecast_rows(client, model)
        actuals.extend(y.iloc[origin:origin + HORIZON].to_list())
        forecasts.extend(float(r[1]) for r in fc)
    log.info("%s: bqml backtest done (%d origins)", series_id, len(list(origins)))
    return {
        "method": METHOD,
        "mape": mape(actuals, forecasts),
        "smape": smape(actuals, forecasts),
        "n_origins": len(list(origins)),
    }


def forecast_with_intervals(client: bigquery.Client, marts: str, ml_dataset: str,
                            series_id: str) -> pd.DataFrame:
    """Full-history fit; the published path when ARIMA_PLUS wins the series."""
    model = f"{ml_dataset}.arima_{series_id.lower()}"
    client.query_and_wait(_train_sql(model, marts, series_id, None))
    rows = _forecast_rows(client, model)
    return pd.DataFrame({
        "step": range(1, HORIZON + 1),
        "forecast": [float(r[1]) for r in rows],
        "lo_95": [float(r[2]) for r in rows],
        "hi_95": [float(r[3]) for r in rows],
    })

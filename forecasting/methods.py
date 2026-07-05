"""Forecasting methods and the rolling-origin harness — pure pandas/numpy in
and out, no warehouse I/O, so every rule here is unit-testable.

Methods are fixed, not searched: a seasonal-naive baseline (the value 52
weeks ago), ETS with damped additive trend, and ARIMA(1,1,1) with drift.
With four series and no holdout beyond the backtest, order-hunting would
just overfit the backtest. The honest comparison is fixed candidates against
the baseline — and the baseline ships wherever it wins (PROJECT_SPEC_V2 §D3).
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

SEASON = 52  # weekly data, annual seasonality
HORIZON = 12  # forecast horizon in weeks
STEP = 4  # rolling-origin step in weeks
MIN_TRAIN = 104  # ≥ 2 years of history before the first origin

BASELINE = "seasonal_naive"


def seasonal_naive(y: pd.Series, horizon: int) -> np.ndarray:
    """ŷ(t+k) = y(t+k−52): this year looks like last year."""
    n = len(y)
    if n < SEASON:
        raise ValueError(f"need at least {SEASON} observations, got {n}")
    return np.array([y.iloc[n + k - SEASON] for k in range(horizon)])


def ets(y: pd.Series, horizon: int) -> np.ndarray:
    return _ets_prediction(y, horizon)["mean"].to_numpy()


def arima(y: pd.Series, horizon: int) -> np.ndarray:
    return _arima_prediction(y, horizon)["mean"].to_numpy()


METHODS = {BASELINE: seasonal_naive, "ets": ets, "arima": arima}


def _ets_prediction(y: pd.Series, horizon: int) -> pd.DataFrame:
    from statsmodels.tsa.exponential_smoothing.ets import ETSModel

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ETSModel(
            y.reset_index(drop=True), error="add", trend="add", damped_trend=True
        ).fit(disp=False)
        pred = fit.get_prediction(start=len(y), end=len(y) + horizon - 1)
        frame = pred.summary_frame(alpha=0.05)
    return frame.rename(columns={"pi_lower": "lo_95", "pi_upper": "hi_95"})


def _arima_prediction(y: pd.Series, horizon: int) -> pd.DataFrame:
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # trend='c' with d=1 is drift — these series trend by construction
        fit = SARIMAX(y.reset_index(drop=True), order=(1, 1, 1), trend="c").fit(disp=False)
        frame = fit.get_forecast(horizon).summary_frame(alpha=0.05)
    return frame.rename(columns={"mean_ci_lower": "lo_95", "mean_ci_upper": "hi_95"})


def mape(actual: np.ndarray, forecast: np.ndarray) -> float:
    actual, forecast = np.asarray(actual, float), np.asarray(forecast, float)
    return float(100 * np.mean(np.abs(forecast - actual) / np.abs(actual)))


def smape(actual: np.ndarray, forecast: np.ndarray) -> float:
    actual, forecast = np.asarray(actual, float), np.asarray(forecast, float)
    denom = np.abs(actual) + np.abs(forecast)
    with np.errstate(invalid="ignore"):
        terms = np.where(denom == 0, 0.0, 2 * np.abs(forecast - actual) / denom)
    return float(100 * np.mean(terms))


def rolling_origin_backtest(y: pd.Series, method, horizon: int = HORIZON,
                            step: int = STEP, min_train: int = MIN_TRAIN) -> pd.DataFrame:
    """Expanding-window forecasts at every origin: fit on y[:o], predict the
    next `horizon` weeks, compare to what actually happened."""
    rows = []
    for origin in range(min_train, len(y) - horizon + 1, step):
        forecasts = method(y.iloc[:origin], horizon)
        actuals = y.iloc[origin:origin + horizon].to_numpy()
        for k in range(horizon):
            rows.append({"origin": origin, "step": k + 1,
                         "actual": actuals[k], "forecast": forecasts[k]})
    if not rows:
        raise ValueError(f"series too short for a backtest: {len(y)} < {min_train + horizon}")
    return pd.DataFrame(rows)


def evaluate(y: pd.Series, methods: dict | None = None) -> pd.DataFrame:
    """One row per method: MAPE, sMAPE, and how many origins the numbers
    stand on. This is the table the dashboard publishes."""
    rows = []
    for name, fn in (methods or METHODS).items():
        bt = rolling_origin_backtest(y, fn)
        rows.append({
            "method": name,
            "mape": mape(bt["actual"], bt["forecast"]),
            "smape": smape(bt["actual"], bt["forecast"]),
            "n_origins": bt["origin"].nunique(),
        })
    return pd.DataFrame(rows)


def select_method(scores: pd.DataFrame) -> str:
    """The spec's publishing rule: a candidate ships only if it beats the
    baseline on sMAPE; otherwise the baseline ships, and the dashboard says
    so. Ties go to the baseline."""
    baseline_smape = float(scores.loc[scores["method"] == BASELINE, "smape"].iloc[0])
    candidates = scores[scores["method"] != BASELINE]
    better = candidates[candidates["smape"] < baseline_smape]
    if better.empty:
        return BASELINE
    return str(better.sort_values("smape").iloc[0]["method"])


def forecast_with_intervals(y: pd.Series, method: str, horizon: int = HORIZON) -> pd.DataFrame:
    """Point forecasts + 95% intervals for the chosen method. The model-based
    methods carry their own intervals; the seasonal-naive baseline gets
    empirical ones — the 2.5th/97.5th percentiles of its own historical
    errors (the lag-52 differences) added to the point. Deliberately
    asymmetric: under drift the naive point sits low, and the interval has
    to cover where actuals land, not flatter the point."""
    if method == BASELINE:
        points = seasonal_naive(y, horizon)
        resid = (y.iloc[SEASON:].to_numpy() - y.iloc[:-SEASON].to_numpy())
        lo_q, hi_q = np.quantile(resid, [0.025, 0.975])
        frame = pd.DataFrame({"mean": points, "lo_95": points + lo_q, "hi_95": points + hi_q})
    elif method == "ets":
        frame = _ets_prediction(y, horizon)
    elif method == "arima":
        frame = _arima_prediction(y, horizon)
    else:
        raise ValueError(f"unknown method {method!r}")
    out = frame[["mean", "lo_95", "hi_95"]].reset_index(drop=True)
    out.insert(0, "step", range(1, horizon + 1))
    return out.rename(columns={"mean": "forecast"})

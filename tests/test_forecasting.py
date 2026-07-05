"""The forecasting harness rules, on synthetic series: the backtest must be
genuinely out-of-sample, the publishing rule must default to the baseline,
and a gap in the weekly grid must stop the run — these are what keep the
published forecast table honest."""

import numpy as np
import pandas as pd
import pytest

from forecasting import methods
from forecasting.h8_forecast import weekly_series


def _trend_series(n=180, start=100.0, slope=0.5, noise=0.0, seed=7):
    rng = np.random.default_rng(seed)
    return pd.Series(
        start + slope * np.arange(n)
        + np.sin(np.arange(n) * 2 * np.pi / 52)
        + noise * rng.standard_normal(n)
    )


def test_seasonal_naive_is_the_year_ago_value():
    y = pd.Series(np.arange(120, dtype=float))
    out = methods.seasonal_naive(y, 3)
    assert list(out) == [120 - 52, 121 - 52, 122 - 52]


def test_seasonal_naive_needs_a_full_season():
    with pytest.raises(ValueError, match="at least 52"):
        methods.seasonal_naive(pd.Series(np.arange(30.0)), 4)


def test_mape_and_smape_known_values():
    actual, forecast = np.array([100.0, 200.0]), np.array([110.0, 180.0])
    assert methods.mape(actual, forecast) == pytest.approx((10 / 100 + 20 / 200) / 2 * 100)
    assert methods.smape(actual, forecast) == pytest.approx(
        (2 * 10 / 210 + 2 * 20 / 380) / 2 * 100
    )


def test_smape_zero_denominator_is_zero_not_nan():
    assert methods.smape(np.array([0.0]), np.array([0.0])) == 0.0


def test_backtest_is_expanding_and_out_of_sample():
    y = _trend_series(140)
    seen = []

    def probe(train, horizon):
        seen.append(len(train))
        return np.full(horizon, train.iloc[-1])

    bt = methods.rolling_origin_backtest(y, probe)
    # origins step by 4 from MIN_TRAIN, and no fold ever sees its own actuals
    assert seen == list(range(methods.MIN_TRAIN, len(y) - methods.HORIZON + 1, methods.STEP))
    first = bt[bt["origin"] == methods.MIN_TRAIN]
    assert list(first["actual"]) == list(y.iloc[104:116])


def test_backtest_rejects_short_series():
    with pytest.raises(ValueError, match="too short"):
        methods.rolling_origin_backtest(pd.Series(np.arange(80.0)), methods.seasonal_naive)


def test_select_method_defaults_to_baseline():
    scores = pd.DataFrame([
        {"method": "seasonal_naive", "smape": 1.0},
        {"method": "ets", "smape": 1.0},     # tie is not a win
        {"method": "arima", "smape": 2.0},
    ])
    assert methods.select_method(scores) == "seasonal_naive"


def test_select_method_picks_the_best_genuine_winner():
    scores = pd.DataFrame([
        {"method": "seasonal_naive", "smape": 2.0},
        {"method": "ets", "smape": 1.5},
        {"method": "arima", "smape": 1.2},
    ])
    assert methods.select_method(scores) == "arima"


def test_baseline_intervals_cover_the_actual_future():
    # the naive point sits low under drift; the empirical interval must still
    # cover where the series actually goes — that's what a fan chart promises
    full = _trend_series(172, noise=0.5)
    y, future = full.iloc[:160], full.iloc[160:172].to_numpy()
    out = methods.forecast_with_intervals(y, "seasonal_naive")
    assert list(out["step"]) == list(range(1, 13))
    assert (out["lo_95"] < out["hi_95"]).all()
    assert ((out["lo_95"].to_numpy() <= future) & (future <= out["hi_95"].to_numpy())).all()


def test_model_methods_produce_finite_paths():
    y = _trend_series(130)
    for name in ("ets", "arima"):
        out = methods.forecast_with_intervals(y, name, horizon=4)
        assert len(out) == 4
        assert np.isfinite(out[["forecast", "lo_95", "hi_95"]].to_numpy()).all()
        assert (out["lo_95"] <= out["forecast"]).all() and (out["forecast"] <= out["hi_95"]).all()


def _h8_frame(dates, series_id="TOTBKCR"):
    return pd.DataFrame({
        "series_id": series_id,
        "series_title": "Bank Credit, All Commercial Banks",
        "obs_date": dates,
        "value_billions": np.linspace(17000, 18000, len(dates)),
    })


def test_weekly_series_clean_grid_passes():
    dates = pd.date_range("2024-01-03", periods=110, freq="7D").date
    y = weekly_series(_h8_frame(list(dates)), "TOTBKCR")
    assert len(y) == 110


def test_weekly_series_gap_stops_the_run():
    dates = list(pd.date_range("2024-01-03", periods=110, freq="7D").date)
    del dates[50]  # a dropped '.' observation leaves a 14-day hole
    with pytest.raises(SystemExit, match="weekly grid has gaps"):
        weekly_series(_h8_frame(dates), "TOTBKCR")

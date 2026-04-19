import numpy as np
import pandas as pd
import pytest

from corridor_backtest.metrics import (
    _total_contributions,
    cagr,
    calmar,
    max_drawdown,
    sharpe,
    sortino,
    summarize,
)


def _make_series(values, start="2020-01-01", freq="D"):
    index = pd.date_range(start=start, periods=len(values), freq=freq)
    return pd.Series(values, index=index, dtype=float)


# ---------------------------------------------------------------------------
# cagr
# ---------------------------------------------------------------------------


def test_cagr_doubles_in_one_year():
    # 252 trading days, value doubles
    pv = _make_series([100.0] + [200.0] * 1, start="2020-01-01")
    pv.index = pd.DatetimeIndex(["2020-01-01", "2021-01-01"])
    result = cagr(pv)
    assert abs(result - 1.0) < 0.01  # ~100% CAGR


def test_cagr_flat_series():
    pv = _make_series([100.0, 100.0])
    pv.index = pd.DatetimeIndex(["2020-01-01", "2021-01-01"])
    assert abs(cagr(pv)) < 1e-10


def test_cagr_positive_growth():
    pv = _make_series([100.0, 110.0, 121.0, 133.1])
    pv.index = pd.DatetimeIndex(
        ["2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01"]
    )
    result = cagr(pv)
    assert result > 0


# ---------------------------------------------------------------------------
# max_drawdown
# ---------------------------------------------------------------------------


def test_max_drawdown_no_drawdown():
    pv = _make_series([100.0, 110.0, 120.0, 130.0])
    assert max_drawdown(pv) == 0.0


def test_max_drawdown_fifty_percent():
    pv = _make_series([100.0, 80.0, 60.0, 50.0, 70.0])
    result = max_drawdown(pv)
    assert abs(result - (-0.50)) < 1e-10


def test_max_drawdown_recovery():
    # drops 20% then recovers -- drawdown is the 20% trough
    pv = _make_series([100.0, 120.0, 96.0, 120.0])
    result = max_drawdown(pv)
    assert abs(result - (-0.20)) < 1e-10


def test_max_drawdown_is_negative():
    pv = _make_series([100.0, 90.0, 80.0])
    assert max_drawdown(pv) < 0


# ---------------------------------------------------------------------------
# sharpe
# ---------------------------------------------------------------------------


def test_sharpe_zero_rf_positive():
    # steadily growing series should have positive Sharpe
    pv = _make_series(np.linspace(100, 200, 252))
    result = sharpe(pv)
    assert result > 0


def test_sharpe_flat_series_is_nan():
    pv = _make_series([100.0] * 10)
    result = sharpe(pv)
    assert np.isnan(result)


def test_sharpe_higher_rf_lowers_ratio():
    pv = _make_series(np.linspace(100, 150, 252))
    s0 = sharpe(pv, risk_free_rate=0.0)
    s1 = sharpe(pv, risk_free_rate=0.05)
    assert s0 > s1


# ---------------------------------------------------------------------------
# sortino
# ---------------------------------------------------------------------------


def test_sortino_positive_for_uptrend():
    # Series with upward drift and some noise so downside returns exist
    rng = np.random.default_rng(42)
    returns = rng.normal(loc=0.001, scale=0.01, size=251)
    prices = np.concatenate([[100.0], 100.0 * np.cumprod(1 + returns)])
    pv = _make_series(prices)
    result = sortino(pv)
    assert result > 0


def test_sortino_higher_than_sharpe_for_uptrend():
    # With mostly positive returns, downside vol < total vol so Sortino > Sharpe
    rng = np.random.default_rng(42)
    returns = rng.normal(loc=0.001, scale=0.01, size=251)
    prices = np.concatenate([[100.0], 100.0 * np.cumprod(1 + returns)])
    pv = _make_series(prices)
    assert sortino(pv) >= sharpe(pv)


# ---------------------------------------------------------------------------
# calmar
# ---------------------------------------------------------------------------


def test_calmar_positive_cagr_and_drawdown():
    pv = _make_series([100.0, 120.0, 90.0, 140.0])
    pv.index = pd.DatetimeIndex(
        ["2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01"]
    )
    result = calmar(pv)
    assert result > 0


def test_calmar_nan_when_no_drawdown():
    pv = _make_series([100.0, 110.0, 120.0])
    pv.index = pd.DatetimeIndex(["2020-01-01", "2021-01-01", "2022-01-01"])
    assert np.isnan(calmar(pv))


# ---------------------------------------------------------------------------
# _total_contributions
# ---------------------------------------------------------------------------


def test_total_contributions_none_config():
    index = pd.date_range("2020-01-01", "2022-01-01", freq="D")
    assert _total_contributions(index, None) == 0.0


def test_total_contributions_no_frequency():
    index = pd.date_range("2020-01-01", "2022-01-01", freq="D")
    assert _total_contributions(index, {"amount": 500, "frequency": None}) == 0.0


def test_total_contributions_monthly():
    index = pd.date_range("2020-01-01", "2021-01-01", freq="D")
    result = _total_contributions(index, {"amount": 500, "frequency": "M"})
    assert result == 12 * 500


def test_total_contributions_quarterly():
    index = pd.date_range("2020-01-01", "2021-01-01", freq="D")
    result = _total_contributions(index, {"amount": 1000, "frequency": "Q"})
    assert result == 4 * 1000


def test_total_contributions_unknown_frequency_returns_zero():
    index = pd.date_range("2020-01-01", "2021-01-01", freq="D")
    assert _total_contributions(index, {"amount": 500, "frequency": "W"}) == 0.0


# ---------------------------------------------------------------------------
# summarize
# ---------------------------------------------------------------------------


def _make_results(n=504):
    index = pd.date_range("2020-01-01", periods=n, freq="B")
    pv = pd.Series(np.linspace(10000, 15000, n), index=index)
    df = pd.DataFrame({"portfolio_value": pv}, index=index)
    df["SPY_weight"] = 0.60
    df["TLT_weight"] = 0.40
    return df


def test_summarize_keys_present():
    results = _make_results()
    rebalance_log = pd.DataFrame()
    config = {
        "name": "test_portfolio",
        "initial_capital": 10000,
        "risk_free_rate": 0.0,
        "contribution": {"amount": 500, "frequency": "M"},
    }
    summary = summarize(results, rebalance_log, config)

    for key in ("cagr", "sharpe", "sortino", "calmar", "max_drawdown",
                "rebalance_count", "final_value", "total_growth"):
        assert key in summary, f"missing key: {key}"


def test_summarize_final_weight_columns():
    results = _make_results()
    config = {
        "name": "test_portfolio",
        "initial_capital": 10000,
        "contribution": None,
    }
    summary = summarize(results, pd.DataFrame(), config)
    assert "SPY_final_weight" in summary
    assert "TLT_final_weight" in summary
    assert abs(summary["SPY_final_weight"] - 0.60) < 1e-10


def test_summarize_with_benchmark():
    results = _make_results()
    index = results.index
    benchmark = pd.Series(np.linspace(100, 130, len(index)), index=index)
    config = {
        "name": "test_portfolio",
        "initial_capital": 10000,
        "contribution": None,
    }
    summary = summarize(results, pd.DataFrame(), config, benchmark=benchmark)
    assert "benchmark_cagr" in summary
    assert "benchmark_sharpe" in summary


def test_summarize_rebalance_count():
    results = _make_results()
    log = pd.DataFrame({"date": pd.date_range("2020-06-01", periods=5, freq="QE")})
    config = {
        "name": "test_portfolio",
        "initial_capital": 10000,
        "contribution": None,
    }
    summary = summarize(results, log, config)
    assert summary["rebalance_count"] == 5


def test_summarize_total_growth():
    results = _make_results()
    config = {
        "name": "test_portfolio",
        "initial_capital": 10000,
        "contribution": {"amount": 0, "frequency": None},
    }
    summary = summarize(results, pd.DataFrame(), config)
    expected_growth = summary["final_value"] - 10000 - summary["total_contributions"]
    assert abs(summary["total_growth"] - expected_growth) < 1e-6

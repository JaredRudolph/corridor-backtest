import numpy as np
import pandas as pd
import pytest

from corridor_backtest.optimize import ROLLING_WINDOW_DAYS, compute_weights


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _synthetic_returns(n_days=600, n_assets=4, seed=42):
    """Return a returns DataFrame with realistic-ish covariance structure."""
    rng = np.random.default_rng(seed)
    means = np.array([0.0004, 0.0002, 0.0001, 0.0003])[:n_assets]
    vols = np.array([0.012, 0.008, 0.007, 0.014])[:n_assets]
    data = rng.normal(loc=means, scale=vols, size=(n_days, n_assets))
    tickers = ["SPY", "TLT", "GLD", "QQQ"][:n_assets]
    index = pd.date_range("2018-01-01", periods=n_days, freq="B")
    return pd.DataFrame(data, index=index, columns=tickers)


# ---------------------------------------------------------------------------
# equal_weight
# ---------------------------------------------------------------------------


def test_equal_weight_four_assets():
    returns = _synthetic_returns(n_assets=4)
    w = compute_weights(returns, "equal_weight")
    np.testing.assert_allclose(w, [0.25, 0.25, 0.25, 0.25])


def test_equal_weight_two_assets():
    returns = _synthetic_returns(n_assets=2)
    w = compute_weights(returns, "equal_weight")
    np.testing.assert_allclose(w, [0.5, 0.5])


def test_equal_weight_ignores_bounds():
    returns = _synthetic_returns(n_assets=2)
    bounds = [(0.3, 0.7), (0.3, 0.7)]
    w = compute_weights(returns, "equal_weight", bounds=bounds)
    np.testing.assert_allclose(w, [0.5, 0.5])


# ---------------------------------------------------------------------------
# Fallback to equal weight when history is too short
# ---------------------------------------------------------------------------


def test_fallback_to_equal_weight_when_insufficient_history():
    # Fewer rows than assets triggers the degenerate covariance fallback
    returns = _synthetic_returns(n_days=3, n_assets=4)
    w = compute_weights(returns, "max_sharpe")
    np.testing.assert_allclose(w, [0.25, 0.25, 0.25, 0.25])


# ---------------------------------------------------------------------------
# Common properties across objectives
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("objective", ["max_sharpe", "max_sortino", "min_vol"])
def test_weights_sum_to_one(objective):
    returns = _synthetic_returns()
    w = compute_weights(returns, objective)
    assert abs(w.sum() - 1.0) < 1e-6


@pytest.mark.parametrize("objective", ["max_sharpe", "max_sortino", "min_vol"])
def test_weights_are_non_negative(objective):
    returns = _synthetic_returns()
    w = compute_weights(returns, objective)
    assert np.all(w >= -1e-8)


@pytest.mark.parametrize("objective", ["max_sharpe", "max_sortino", "min_vol"])
def test_weights_length_matches_assets(objective):
    returns = _synthetic_returns(n_assets=3)
    w = compute_weights(returns, objective)
    assert len(w) == 3


# ---------------------------------------------------------------------------
# Bounds enforcement
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("objective", ["max_sharpe", "max_sortino", "min_vol"])
def test_bounds_respected(objective):
    returns = _synthetic_returns()
    bounds = [(0.10, 0.40)] * 4
    w = compute_weights(returns, objective, bounds=bounds)
    assert np.all(w >= 0.10 - 1e-6)
    assert np.all(w <= 0.40 + 1e-6)


def test_min_vol_with_bounds_sums_to_one():
    returns = _synthetic_returns()
    bounds = [(0.05, 0.50)] * 4
    w = compute_weights(returns, "min_vol", bounds=bounds)
    assert abs(w.sum() - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# min_vol produces lower volatility than equal weight
# ---------------------------------------------------------------------------


def test_min_vol_lower_variance_than_equal_weight():
    returns = _synthetic_returns()
    window = returns.iloc[-ROLLING_WINDOW_DAYS:]
    cov = window.cov().values

    w_eq = compute_weights(returns, "equal_weight")
    w_mv = compute_weights(returns, "min_vol")

    var_eq = w_eq @ cov @ w_eq
    var_mv = w_mv @ cov @ w_mv

    assert var_mv <= var_eq + 1e-8


# ---------------------------------------------------------------------------
# max_sharpe with bounds produces higher Sharpe than min_vol
# ---------------------------------------------------------------------------


def test_max_sharpe_beats_min_vol_on_sharpe():
    returns = _synthetic_returns()
    window = returns.iloc[-ROLLING_WINDOW_DAYS:]
    mean_r = window.mean().values * 252
    cov = window.cov().values

    bounds = [(0.05, 0.60)] * 4
    w_sharpe = compute_weights(returns, "max_sharpe", bounds=bounds)
    w_mv = compute_weights(returns, "min_vol", bounds=bounds)

    def ann_sharpe(w):
        ret = w @ mean_r
        vol = np.sqrt(w @ cov @ w * 252)
        return ret / vol

    assert ann_sharpe(w_sharpe) >= ann_sharpe(w_mv) - 1e-4


# ---------------------------------------------------------------------------
# Unknown objective raises
# ---------------------------------------------------------------------------


def test_unknown_objective_raises():
    returns = _synthetic_returns()
    with pytest.raises(ValueError, match="Unknown objective"):
        compute_weights(returns, "magic")

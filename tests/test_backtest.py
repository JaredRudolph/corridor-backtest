import numpy as np
import pandas as pd
import pytest

from corridor_backtest.backtest import (
    _apply_contribution,
    _contribution_due,
    _resolve_bounds,
    run_backtest,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_prices(n_days=504, seed=42):
    """Two-asset price DataFrame with realistic-ish returns."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(loc=0.0003, scale=0.01, size=(n_days, 2))
    prices = np.cumprod(1 + returns, axis=0) * 100
    index = pd.date_range("2020-01-01", periods=n_days, freq="B")
    return pd.DataFrame(prices, index=index, columns=["SPY", "TLT"])


def _base_config(**overrides):
    cfg = {
        "name": "test",
        "tickers": ["SPY", "TLT"],
        "weights": {"SPY": 0.60, "TLT": 0.40},
        "benchmark": "SPY",
        "initial_capital": 10000,
        "contribution": None,
        "rebalance": {
            "mode": "none",
            "threshold_type": "absolute",
            "band": 0.05,
            "rebalance_to": "target",
            "schedule": "Q",
        },
    }
    cfg.update(overrides)
    return cfg


# ---------------------------------------------------------------------------
# _contribution_due
# ---------------------------------------------------------------------------


def test_contribution_due_monthly_new_month():
    assert _contribution_due(
        pd.Timestamp("2023-02-01"), "M", pd.Timestamp("2023-01-31")
    )


def test_contribution_due_monthly_same_month():
    assert not _contribution_due(
        pd.Timestamp("2023-01-15"), "M", pd.Timestamp("2023-01-01")
    )


def test_contribution_due_quarterly_new_quarter():
    assert _contribution_due(
        pd.Timestamp("2023-04-01"), "Q", pd.Timestamp("2023-03-31")
    )


def test_contribution_due_quarterly_same_quarter():
    assert not _contribution_due(
        pd.Timestamp("2023-02-15"), "Q", pd.Timestamp("2023-01-01")
    )


def test_contribution_due_unknown_frequency_raises():
    with pytest.raises(ValueError, match="Unknown contribution frequency"):
        _contribution_due(pd.Timestamp("2023-01-01"), "W", pd.Timestamp("2022-12-01"))


# ---------------------------------------------------------------------------
# _apply_contribution
# ---------------------------------------------------------------------------


def _prices_series(a=100.0, b=50.0):
    return pd.Series({"SPY": a, "TLT": b})


def test_apply_contribution_pro_rata_increases_shares():
    shares = np.array([6.0, 8.0])
    prices = _prices_series()
    targets = np.array([0.60, 0.40])
    portfolio_value = 1000.0
    cfg = {"amount": 500, "method": "pro_rata"}

    new_shares = _apply_contribution(shares, prices, portfolio_value, targets, cfg)

    # pro_rata: $300 into SPY @ $100 = 3 extra shares; $200 into TLT @ $50 = 4 extra
    np.testing.assert_allclose(new_shares, [9.0, 12.0])


def test_apply_contribution_smart_buys_most_underweight():
    # SPY at 50% weight, target 60% -- most underweight
    prices = _prices_series(100.0, 100.0)
    portfolio_value = 1000.0
    shares = np.array([5.0, 5.0])  # 50/50 split
    targets = np.array([0.60, 0.40])
    cfg = {"amount": 200, "method": "smart"}

    new_shares = _apply_contribution(shares, prices, portfolio_value, targets, cfg)

    # All $200 goes to SPY (index 0): 2 more shares
    assert new_shares[0] == pytest.approx(7.0)
    assert new_shares[1] == pytest.approx(5.0)


def test_apply_contribution_unknown_method_raises():
    with pytest.raises(ValueError, match="Unknown contribution method"):
        _apply_contribution(
            np.array([5.0, 5.0]),
            _prices_series(),
            1000.0,
            np.array([0.5, 0.5]),
            {"amount": 100, "method": "random"},
        )


# ---------------------------------------------------------------------------
# _resolve_bounds
# ---------------------------------------------------------------------------


def test_resolve_bounds_none_returns_long_only():
    bounds = _resolve_bounds({}, {"SPY": 0.6, "TLT": 0.4}, ["SPY", "TLT"])
    assert bounds == [(0.0, None), (0.0, None)]


def test_resolve_bounds_lazy_global():
    optimize_cfg = {"weight_bounds": {"min": 0.5, "max": 1.5}}
    bounds = _resolve_bounds(
        optimize_cfg, {"SPY": 0.60, "TLT": 0.40}, ["SPY", "TLT"]
    )
    assert bounds[0] == pytest.approx((0.30, 0.90))
    assert bounds[1] == pytest.approx((0.20, 0.60))


def test_resolve_bounds_per_asset():
    optimize_cfg = {
        "weight_bounds": {"SPY": [0.10, 0.70], "TLT": [0.05, 0.50]}
    }
    bounds = _resolve_bounds(
        optimize_cfg, {"SPY": 0.60, "TLT": 0.40}, ["SPY", "TLT"]
    )
    assert bounds[0] == (0.10, 0.70)
    assert bounds[1] == (0.05, 0.50)


def test_resolve_bounds_per_asset_missing_ticker_raises():
    optimize_cfg = {"weight_bounds": {"SPY": [0.10, 0.70]}}
    with pytest.raises(KeyError, match="TLT"):
        _resolve_bounds(
            optimize_cfg, {"SPY": 0.60, "TLT": 0.40}, ["SPY", "TLT"]
        )


# ---------------------------------------------------------------------------
# run_backtest -- structural checks
# ---------------------------------------------------------------------------


def test_run_backtest_missing_ticker_raises():
    prices = _make_prices()
    cfg = _base_config(tickers=["SPY", "MISSING"])
    with pytest.raises(KeyError, match="MISSING"):
        run_backtest(prices, cfg)


def test_run_backtest_returns_correct_index():
    prices = _make_prices()
    cfg = _base_config()
    results, _ = run_backtest(prices, cfg)
    assert list(results.index) == list(prices.index)


def test_run_backtest_portfolio_value_starts_near_initial_capital():
    prices = _make_prices()
    cfg = _base_config()
    results, _ = run_backtest(prices, cfg)
    assert results["portfolio_value"].iloc[0] == pytest.approx(10000.0, rel=1e-3)


def test_run_backtest_weight_columns_present():
    prices = _make_prices()
    cfg = _base_config()
    results, _ = run_backtest(prices, cfg)
    assert "SPY_weight" in results.columns
    assert "TLT_weight" in results.columns


def test_run_backtest_weights_sum_to_one():
    prices = _make_prices()
    cfg = _base_config()
    results, _ = run_backtest(prices, cfg)
    weight_sum = results["SPY_weight"] + results["TLT_weight"]
    np.testing.assert_allclose(weight_sum.values, 1.0, atol=1e-8)


# ---------------------------------------------------------------------------
# run_backtest -- mode: none
# ---------------------------------------------------------------------------


def test_run_backtest_mode_none_no_rebalances():
    prices = _make_prices()
    cfg = _base_config()
    results, log = run_backtest(prices, cfg)
    assert results["rebalanced"].sum() == 0
    assert len(log) == 0


# ---------------------------------------------------------------------------
# run_backtest -- mode: periodic
# ---------------------------------------------------------------------------


def test_run_backtest_periodic_fires_rebalances():
    prices = _make_prices(n_days=504)
    cfg = _base_config(
        rebalance={
            "mode": "periodic",
            "threshold_type": "absolute",
            "band": 0.05,
            "rebalance_to": "target",
            "schedule": "Q",
        }
    )
    results, log = run_backtest(prices, cfg)
    assert results["rebalanced"].sum() > 0
    assert len(log) > 0


def test_run_backtest_periodic_log_trigger_label():
    prices = _make_prices(n_days=504)
    cfg = _base_config(
        rebalance={
            "mode": "periodic",
            "threshold_type": "absolute",
            "band": 0.05,
            "rebalance_to": "target",
            "schedule": "Q",
        }
    )
    _, log = run_backtest(prices, cfg)
    assert set(log["trigger"].unique()) == {"periodic"}


# ---------------------------------------------------------------------------
# run_backtest -- contributions
# ---------------------------------------------------------------------------


def test_run_backtest_contribution_grows_portfolio_value():
    prices = _make_prices(n_days=504, seed=0)
    cfg_no_contrib = _base_config()
    cfg_contrib = _base_config(
        contribution={"amount": 500, "frequency": "M", "method": "pro_rata"}
    )
    results_no, _ = run_backtest(prices, cfg_no_contrib)
    results_yes, _ = run_backtest(prices, cfg_contrib)
    assert (
        results_yes["portfolio_value"].iloc[-1]
        > results_no["portfolio_value"].iloc[-1]
    )


# ---------------------------------------------------------------------------
# run_backtest -- corridor rebalance snaps weights back to target
# ---------------------------------------------------------------------------


def test_run_backtest_corridor_post_weights_near_target():
    prices = _make_prices(n_days=504)
    cfg = _base_config(
        rebalance={
            "mode": "corridor",
            "threshold_type": "absolute",
            "band": 0.01,  # tight band to force frequent rebalances
            "rebalance_to": "target",
            "schedule": "Q",
        }
    )
    _, log = run_backtest(prices, cfg)
    if len(log) > 0:
        np.testing.assert_allclose(
            log["SPY_post"].values, 0.60, atol=0.01
        )
        np.testing.assert_allclose(
            log["TLT_post"].values, 0.40, atol=0.01
        )

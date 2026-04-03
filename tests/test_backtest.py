import pytest

from allocator.backtest import run_backtest


def test_output_shape(synthetic_prices, base_config):
    results, events = run_backtest(synthetic_prices, base_config)
    assert len(results) == len(synthetic_prices)
    for col in ("portfolio_value", "rebalanced", "contribution"):
        assert col in results.columns


def test_portfolio_value_always_positive(synthetic_prices, base_config):
    results, _ = run_backtest(synthetic_prices, base_config)
    assert (results["portfolio_value"] > 0).all()


def test_weights_sum_to_one(synthetic_prices, base_config):
    results, _ = run_backtest(synthetic_prices, base_config)
    weight_cols = [c for c in results.columns if c.startswith("weight_")]
    sums = results[weight_cols].sum(axis=1)
    assert (abs(sums - 1.0) < 1e-6).all()


def test_missing_ticker_raises(synthetic_prices, base_config):
    cfg = {**base_config, "tickers": ["A", "B", "MISSING"]}
    with pytest.raises(KeyError):
        run_backtest(synthetic_prices, cfg)


def test_contributions_applied(synthetic_prices, base_config):
    results, _ = run_backtest(synthetic_prices, base_config)
    # Over ~2.4 years with monthly contributions there should be many non-zero rows
    assert (results["contribution"] > 0).sum() > 20


def test_pro_rata_contribution(synthetic_prices, base_config):
    cfg = {**base_config, "contribution": {**base_config["contribution"], "method": "pro_rata"}}
    results, _ = run_backtest(synthetic_prices, cfg)
    assert (results["portfolio_value"] > 0).all()


def test_periodic_mode(synthetic_prices, base_config):
    cfg = {**base_config}
    cfg["rebalance"] = {
        "mode": "periodic",
        "threshold_type": "relative",
        "band": 0.10,
        "schedule": "Q",
    }
    results, events = run_backtest(synthetic_prices, cfg)
    assert len(results) == len(synthetic_prices)
    # Quarterly over ~2.4 years: expect around 8-10 rebalances
    assert 5 <= len(events) <= 15


def test_hybrid_mode(synthetic_prices, base_config):
    cfg = {**base_config}
    cfg["rebalance"] = {
        "mode": "hybrid",
        "threshold_type": "relative",
        "band": 0.05,
        "schedule": "Q",
    }
    results, events = run_backtest(synthetic_prices, cfg)
    assert (results["portfolio_value"] > 0).all()

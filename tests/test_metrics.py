import pytest

from allocator.backtest import run_backtest
from allocator.metrics import compute_metrics


def _run(synthetic_prices, base_config):
    results, events = run_backtest(synthetic_prices, base_config)
    benchmark = synthetic_prices["A"]
    metrics = compute_metrics(results, benchmark, base_config, events)
    return results, events, metrics


def test_top_level_keys(synthetic_prices, base_config):
    _, _, metrics = _run(synthetic_prices, base_config)
    for key in ("portfolio", "benchmark", "rebalance_events", "total_contributions", "growth"):
        assert key in metrics


def test_portfolio_and_benchmark_fields(synthetic_prices, base_config):
    _, _, metrics = _run(synthetic_prices, base_config)
    for section in ("portfolio", "benchmark"):
        for field in ("cagr", "sharpe", "max_drawdown", "final_value"):
            assert field in metrics[section]


def test_max_drawdown_nonpositive(synthetic_prices, base_config):
    _, _, metrics = _run(synthetic_prices, base_config)
    assert metrics["portfolio"]["max_drawdown"] <= 0
    assert metrics["benchmark"]["max_drawdown"] <= 0


def test_total_contributions_matches_results(synthetic_prices, base_config):
    results, events, metrics = _run(synthetic_prices, base_config)
    assert abs(metrics["total_contributions"] - results["contribution"].sum()) < 1e-6


def test_rebalance_event_count(synthetic_prices, base_config):
    _, events, metrics = _run(synthetic_prices, base_config)
    assert metrics["rebalance_events"] == len(events)

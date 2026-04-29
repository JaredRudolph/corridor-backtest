import numpy as np
import pandas as pd
import pytest

from corridor_backtest.pipeline import run_pipeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_prices(n_days=504, tickers=("SPY", "TLT"), seed=3):
    rng = np.random.default_rng(seed)
    n = len(tickers)
    returns = rng.normal(loc=0.0003, scale=0.01, size=(n_days, n))
    prices = np.cumprod(1 + returns, axis=0) * 100
    index = pd.date_range("2020-01-01", periods=n_days, freq="B")
    return pd.DataFrame(prices, index=index, columns=list(tickers))


def _base_config(name="p1", tickers=("SPY", "TLT")):
    return {
        "name": name,
        "tickers": list(tickers),
        "weights": {t: 1.0 / len(tickers) for t in tickers},
        "benchmark": "SPY",
        "start": "2020-01-01",
        "end": None,
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


@pytest.fixture
def patch_fetch(monkeypatch):
    """Replace fetch_prices with a factory that returns synthetic prices."""

    def _fetch(tickers, start, end=None):
        return _make_prices(tickers=tickers)

    monkeypatch.setattr("corridor_backtest.pipeline.fetch_prices", _fetch)


# ---------------------------------------------------------------------------
# Return structure
# ---------------------------------------------------------------------------


def test_run_pipeline_returns_tuple(patch_fetch):
    result = run_pipeline([_base_config()])
    assert isinstance(result, tuple) and len(result) == 2


def test_run_pipeline_comparison_is_dataframe(patch_fetch):
    comparison, _ = run_pipeline([_base_config()])
    assert isinstance(comparison, pd.DataFrame)


def test_run_pipeline_portfolio_data_is_list(patch_fetch):
    _, portfolio_data = run_pipeline([_base_config()])
    assert isinstance(portfolio_data, list)


# ---------------------------------------------------------------------------
# Single portfolio
# ---------------------------------------------------------------------------


def test_run_pipeline_single_portfolio_one_row(patch_fetch):
    comparison, _ = run_pipeline([_base_config()])
    assert len(comparison) == 1


def test_run_pipeline_index_is_portfolio_name(patch_fetch):
    comparison, _ = run_pipeline([_base_config(name="my_port")])
    assert comparison.index[0] == "my_port"


def test_run_pipeline_portfolio_data_keys(patch_fetch):
    _, portfolio_data = run_pipeline([_base_config()])
    entry = portfolio_data[0]
    assert {"name", "results", "rebalance_log"} <= set(entry.keys())


def test_run_pipeline_results_has_portfolio_value(patch_fetch):
    _, portfolio_data = run_pipeline([_base_config()])
    assert "portfolio_value" in portfolio_data[0]["results"].columns


# ---------------------------------------------------------------------------
# Multiple portfolios
# ---------------------------------------------------------------------------


def test_run_pipeline_multiple_portfolios_row_count(patch_fetch):
    configs = [_base_config("a"), _base_config("b"), _base_config("c")]
    comparison, portfolio_data = run_pipeline(configs)
    assert len(comparison) == 3
    assert len(portfolio_data) == 3


def test_run_pipeline_multiple_portfolios_index_names(patch_fetch):
    configs = [_base_config("alpha"), _base_config("beta")]
    comparison, _ = run_pipeline(configs)
    assert list(comparison.index) == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# Metric columns present
# ---------------------------------------------------------------------------


def test_run_pipeline_metric_columns_present(patch_fetch):
    comparison, _ = run_pipeline([_base_config()])
    for col in ("cagr", "sharpe", "sortino", "calmar", "max_drawdown"):
        assert col in comparison.columns, f"missing column: {col}"


def test_run_pipeline_benchmark_metrics_present(patch_fetch):
    comparison, _ = run_pipeline([_base_config()])
    assert "benchmark_cagr" in comparison.columns
    assert "benchmark_sharpe" in comparison.columns


# ---------------------------------------------------------------------------
# band_search integration
# ---------------------------------------------------------------------------


def test_run_pipeline_band_search_runs_without_error(patch_fetch):
    cfg = _base_config()
    cfg["rebalance"]["mode"] = "corridor"
    cfg["band_search"] = {"metric": "sharpe", "band_range": [0.02, 0.15], "steps": 4}
    comparison, _ = run_pipeline([cfg])
    assert len(comparison) == 1


def test_run_pipeline_band_search_patches_best_band(monkeypatch):
    """Best band from search_band should be used in the final backtest."""
    captured = {}

    def _fetch(tickers, start, end=None):
        return _make_prices(tickers=tickers)

    def _search_band(prices, config):
        from corridor_backtest.band_search import search_band as real_search_band

        best_params, results = real_search_band(prices, config)
        captured["best_band"] = best_params
        return best_params, results

    monkeypatch.setattr("corridor_backtest.pipeline.fetch_prices", _fetch)
    monkeypatch.setattr("corridor_backtest.pipeline.search_band", _search_band)

    cfg = _base_config()
    cfg["rebalance"]["mode"] = "corridor"
    cfg["band_search"] = {"metric": "cagr", "band_range": [0.02, 0.15], "steps": 4}

    run_pipeline([cfg])
    assert "best_band" in captured

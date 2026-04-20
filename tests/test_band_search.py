import numpy as np
import pandas as pd
import pytest

from corridor_backtest.band_search import search_band

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_prices(n_days=504, seed=7):
    rng = np.random.default_rng(seed)
    returns = rng.normal(loc=0.0003, scale=0.01, size=(n_days, 2))
    prices = np.cumprod(1 + returns, axis=0) * 100
    index = pd.date_range("2020-01-01", periods=n_days, freq="B")
    return pd.DataFrame(prices, index=index, columns=["SPY", "TLT"])


def _base_config(metric="sharpe", steps=5):
    return {
        "name": "test",
        "tickers": ["SPY", "TLT"],
        "weights": {"SPY": 0.60, "TLT": 0.40},
        "initial_capital": 10000,
        "contribution": None,
        "rebalance": {
            "mode": "corridor",
            "threshold_type": "absolute",
            "rebalance_to": "target",
            "band": 0.05,
            "schedule": "Q",
        },
        "band_search": {
            "metric": metric,
            "band_range": [0.02, 0.20],
            "steps": steps,
        },
    }


# ---------------------------------------------------------------------------
# Return structure
# ---------------------------------------------------------------------------


def test_search_band_returns_tuple():
    prices = _make_prices()
    result = search_band(prices, _base_config())
    assert isinstance(result, tuple) and len(result) == 2


def test_search_band_best_band_is_float():
    prices = _make_prices()
    best_band, _ = search_band(prices, _base_config())
    assert isinstance(best_band, float)


def test_search_band_results_columns():
    prices = _make_prices()
    _, results = search_band(prices, _base_config())
    assert set(results.columns) >= {"band", "metric", "score"}


def test_search_band_results_row_count_matches_steps():
    prices = _make_prices()
    steps = 6
    _, results = search_band(prices, _base_config(steps=steps))
    assert len(results) == steps


def test_search_band_results_sorted_descending():
    prices = _make_prices()
    _, results = search_band(prices, _base_config())
    scores = results["score"].values
    assert np.all(scores[:-1] >= scores[1:])


# ---------------------------------------------------------------------------
# best_band is within the searched range
# ---------------------------------------------------------------------------


def test_search_band_best_band_within_range():
    prices = _make_prices()
    cfg = _base_config()
    lo, hi = cfg["band_search"]["band_range"]
    best_band, _ = search_band(prices, cfg)
    assert lo - 1e-9 <= best_band <= hi + 1e-9


# ---------------------------------------------------------------------------
# best_band matches the top row of search_results
# ---------------------------------------------------------------------------


def test_search_band_best_band_matches_top_row():
    prices = _make_prices()
    best_band, results = search_band(prices, _base_config())
    assert best_band == pytest.approx(results.iloc[0]["band"])


# ---------------------------------------------------------------------------
# All supported metrics run without error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("metric", ["sharpe", "cagr", "calmar", "sortino"])
def test_search_band_all_metrics(metric):
    prices = _make_prices()
    best_band, results = search_band(prices, _base_config(metric=metric))
    assert np.isfinite(best_band)
    assert results["metric"].iloc[0] == metric


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_search_band_unknown_metric_raises():
    prices = _make_prices()
    cfg = _base_config()
    cfg["band_search"]["metric"] = "magic"
    with pytest.raises(ValueError, match="Unknown metric"):
        search_band(prices, cfg)


def test_search_band_missing_band_search_key_raises():
    prices = _make_prices()
    cfg = _base_config()
    del cfg["band_search"]
    with pytest.raises(KeyError):
        search_band(prices, cfg)

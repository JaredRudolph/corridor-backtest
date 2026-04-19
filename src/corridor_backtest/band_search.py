import numpy as np
import pandas as pd

from corridor_backtest.backtest import run_backtest
from corridor_backtest.metrics import cagr, calmar, sharpe, sortino

_METRIC_FNS = {
    "sharpe": sharpe,
    "cagr": cagr,
    "calmar": calmar,
    "sortino": sortino,
}


def search_band(prices: pd.DataFrame, config: dict) -> tuple[float, pd.DataFrame]:
    """Search over band widths to find the value that maximizes a chosen metric.

    Iterates over evenly spaced band candidates, runs a full backtest for each,
    and scores the result using the metric specified in config['band_search'].

    Args:
        prices: Date-indexed DataFrame of adjusted close prices.
        config: Portfolio config dict containing a 'band_search' key.

    Returns:
        Tuple of (best_band, search_results) where:
          - best_band: The band value that produced the highest metric score.
          - search_results: DataFrame with columns ['band', 'metric', 'score'],
            sorted descending by score.

    Raises:
        KeyError: If 'band_search' is not present in config.
        ValueError: If the metric name is not recognized.
    """
    band_cfg = config["band_search"]
    metric_name = band_cfg["metric"]
    lo, hi = band_cfg["band_range"]
    steps = band_cfg["steps"]
    risk_free_rate = config.get("risk_free_rate", 0.0)

    if metric_name not in _METRIC_FNS:
        raise ValueError(
            f"Unknown metric '{metric_name}'. Use one of: {list(_METRIC_FNS)}."
        )

    metric_fn = _METRIC_FNS[metric_name]
    candidates = np.linspace(lo, hi, steps)
    records = []

    for band in candidates:
        candidate_cfg = {**config, "rebalance": {**config["rebalance"], "band": band}}
        results, _ = run_backtest(prices, candidate_cfg)
        pv = results["portfolio_value"]

        if metric_name in ("sharpe", "sortino"):
            score = metric_fn(pv, risk_free_rate)
        else:
            score = metric_fn(pv)

        records.append({"band": band, "metric": metric_name, "score": score})

    search_results = (
        pd.DataFrame(records)
        .sort_values("score", ascending=False)
        .reset_index(drop=True)
    )
    best_band = float(search_results.iloc[0]["band"])

    return best_band, search_results

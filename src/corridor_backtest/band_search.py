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


def search_band(prices: pd.DataFrame, config: dict) -> tuple[dict, pd.DataFrame]:
    """Search over band/corridor widths to find values that maximize a chosen metric.

    Prices should already be sliced to the desired search window (e.g. train split)
    before being passed in. The caller is responsible for windowing.

    In 1D mode (no 'corridor_range' in band_search config): searches over a single
    parameter -- 'corridor' if the rebalance config has a 'corridor' key, else 'band'.

    In 2D mode ('corridor_range' present in band_search config): searches over all
    valid (band, corridor) pairs where corridor > band, running a full backtest for
    each combination.

    A 'robust' boolean column is added to search_results marking candidates whose
    score is within robustness_threshold of the best score. Defaults to 0.95.

    Args:
        prices: Date-indexed DataFrame of adjusted close prices (train window).
        config: Portfolio config dict containing a 'band_search' key.

    Returns:
        Tuple of (best_params, search_results) where:
          - best_params: Dict mapping parameter name(s) to optimal value(s).
            1D: {'band': val} or {'corridor': val}.
            2D: {'band': val, 'corridor': val}.
          - search_results: DataFrame sorted descending by score. Columns are
            ['band', 'metric', 'score', 'robust'] for 1D or
            ['band', 'corridor', 'metric', 'score', 'robust'] for 2D.

    Raises:
        KeyError: If 'band_search' is not present in config.
        ValueError: If the metric name is not recognized.
    """
    band_cfg = config["band_search"]
    metric_name = band_cfg["metric"]
    risk_free_rate = config.get("risk_free_rate", 0.0)
    robustness_threshold = band_cfg.get("robustness_threshold", 0.95)

    if metric_name not in _METRIC_FNS:
        raise ValueError(
            f"Unknown metric '{metric_name}'. Use one of: {list(_METRIC_FNS)}."
        )

    metric_fn = _METRIC_FNS[metric_name]

    def _score(cfg):
        results, _ = run_backtest(prices, cfg)
        pv = results["portfolio_value"]
        return (
            metric_fn(pv, risk_free_rate)
            if metric_name in ("sharpe", "sortino")
            else metric_fn(pv)
        )

    def _mark_robust(df: pd.DataFrame) -> pd.DataFrame:
        best = df["score"].iloc[0]
        df["robust"] = df["score"] >= robustness_threshold * best
        return df

    if "corridor_range" in band_cfg:
        band_lo, band_hi = band_cfg["band_range"]
        corr_lo, corr_hi = band_cfg["corridor_range"]
        steps = band_cfg["steps"]
        band_candidates = np.linspace(band_lo, band_hi, steps)
        corr_candidates = np.linspace(corr_lo, corr_hi, steps)

        records = []
        for b in band_candidates:
            for c in corr_candidates:
                if c <= b:
                    continue
                candidate_cfg = {
                    **config,
                    "rebalance": {**config["rebalance"], "band": b, "corridor": c},
                }
                records.append(
                    {
                        "band": b,
                        "corridor": c,
                        "metric": metric_name,
                        "score": _score(candidate_cfg),
                    }
                )

        search_results = _mark_robust(
            pd.DataFrame(records)
            .sort_values("score", ascending=False)
            .reset_index(drop=True)
        )
        best = search_results.iloc[0]
        return {
            "band": float(best["band"]),
            "corridor": float(best["corridor"]),
        }, search_results

    else:
        lo, hi = band_cfg["band_range"]
        steps = max(band_cfg["steps"], 30)
        search_key = "corridor" if "corridor" in config["rebalance"] else "band"
        candidates = np.linspace(lo, hi, steps)

        records = []
        for val in candidates:
            candidate_cfg = {
                **config,
                "rebalance": {**config["rebalance"], search_key: val},
            }
            records.append(
                {"band": val, "metric": metric_name, "score": _score(candidate_cfg)}
            )

        search_results = _mark_robust(
            pd.DataFrame(records)
            .sort_values("score", ascending=False)
            .reset_index(drop=True)
        )
        best_val = float(search_results.iloc[0]["band"])
        return {search_key: best_val}, search_results

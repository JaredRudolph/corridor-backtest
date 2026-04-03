import numpy as np
import pandas as pd

from .rebalance import RebalanceEvent


def compute_metrics(
    results: pd.DataFrame,
    benchmark_prices: pd.Series,
    cfg: dict,
    events: list[RebalanceEvent],
) -> dict:
    """Compute performance metrics for the portfolio and benchmark."""
    port_values = results["portfolio_value"]
    port_returns = port_values.pct_change().dropna()
    rf = cfg.get("risk_free_rate", 0.0)

    portfolio = _series_metrics(port_values, port_returns, rf)

    bench = benchmark_prices.reindex(port_values.index).ffill()
    bench_returns = bench.pct_change().dropna()
    benchmark = _series_metrics(bench, bench_returns, rf)

    total_contributed = float(results["contribution"].sum())
    growth = float(port_values.iloc[-1]) - cfg["initial_capital"] - total_contributed

    return {
        "portfolio": portfolio,
        "benchmark": benchmark,
        "rebalance_events": len(events),
        "total_contributions": total_contributed,
        "growth": growth,
    }


def _series_metrics(
    values: pd.Series, returns: pd.Series, rf: float
) -> dict:
    n_years = (values.index[-1] - values.index[0]).days / 365.25
    cagr = float((values.iloc[-1] / values.iloc[0]) ** (1.0 / n_years) - 1.0)

    excess = returns - rf / 252
    sharpe = (
        float((excess.mean() / excess.std()) * np.sqrt(252))
        if excess.std() > 1e-12
        else 0.0
    )

    rolling_max = values.cummax()
    max_drawdown = float((values / rolling_max - 1.0).min())

    return {
        "cagr": cagr,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "final_value": float(values.iloc[-1]),
    }

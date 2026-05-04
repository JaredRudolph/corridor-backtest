import numpy as np
import pandas as pd


def cagr(portfolio_value: pd.Series) -> float:
    """Compute compound annual growth rate.

    Args:
        portfolio_value: Date-indexed series of portfolio values.

    Returns:
        CAGR as a decimal (e.g. 0.08 for 8%).
    """
    years = (portfolio_value.index[-1] - portfolio_value.index[0]).days / 365.25
    return (portfolio_value.iloc[-1] / portfolio_value.iloc[0]) ** (1 / years) - 1


def max_drawdown(portfolio_value: pd.Series) -> float:
    """Compute the maximum peak-to-trough drawdown.

    Args:
        portfolio_value: Date-indexed series of portfolio values.

    Returns:
        Max drawdown as a negative decimal (e.g. -0.35 for a 35% drawdown).
    """
    peak = portfolio_value.cummax()
    drawdown = (portfolio_value - peak) / peak
    return float(drawdown.min())


def sharpe(portfolio_value: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Compute the annualized Sharpe ratio.

    Args:
        portfolio_value: Date-indexed series of portfolio values.
        risk_free_rate: Annualized risk-free rate.

    Returns:
        Annualized Sharpe ratio.
    """
    daily_returns = portfolio_value.pct_change().dropna()
    daily_rf = risk_free_rate / 252
    excess = daily_returns - daily_rf
    std = excess.std()
    if std == 0:
        return float("nan")
    return float(excess.mean() / std * np.sqrt(252))


def sortino(portfolio_value: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Compute the annualized Sortino ratio.

    Args:
        portfolio_value: Date-indexed series of portfolio values.
        risk_free_rate: Annualized risk-free rate.

    Returns:
        Annualized Sortino ratio.
    """
    daily_returns = portfolio_value.pct_change().dropna()
    daily_rf = risk_free_rate / 252
    excess = daily_returns - daily_rf
    downside = excess[excess < 0]
    downside_std = np.sqrt((downside**2).mean())
    return float(excess.mean() / downside_std * np.sqrt(252))


def calmar(portfolio_value: pd.Series) -> float:
    """Compute the Calmar ratio (CAGR / absolute max drawdown).

    Args:
        portfolio_value: Date-indexed series of portfolio values.

    Returns:
        Calmar ratio. Returns NaN if max drawdown is zero.
    """
    mdd = max_drawdown(portfolio_value)
    if mdd == 0:
        return float("nan")
    return cagr(portfolio_value) / abs(mdd)


def summarize(
    results: pd.DataFrame,
    rebalance_log: pd.DataFrame,
    config: dict,
    benchmark: pd.Series | None = None,
) -> dict:
    """Compute all performance metrics for a single portfolio backtest.

    Args:
        results: Date-indexed DataFrame from run_backtest, must contain
            'portfolio_value'.
        rebalance_log: DataFrame of rebalance events from run_backtest.
        config: The portfolio config dict.
        benchmark: Optional date-indexed price series for the benchmark ticker.

    Returns:
        Flat dict of metrics for this portfolio.
    """
    pv = results["portfolio_value"]
    risk_free_rate = config.get("risk_free_rate", 0.0)

    years = (pv.index[-1] - pv.index[0]).days / 365.25
    rebalance_count = len(rebalance_log)

    contribution_cfg = config.get("contribution")
    total_contributions = _total_contributions(pv.index, contribution_cfg)

    summary = {
        "name": config["name"],
        "cagr": cagr(pv),
        "sharpe": sharpe(pv, risk_free_rate),
        "sortino": sortino(pv, risk_free_rate),
        "calmar": calmar(pv),
        "max_drawdown": max_drawdown(pv),
        "rebalance_count": rebalance_count,
        "rebalance_freq_per_year": rebalance_count / years
        if years > 0
        else float("nan"),
        "transaction_costs": results.attrs.get("total_transaction_costs", 0.0),
        "initial_capital": config["initial_capital"],
        "total_contributions": total_contributions,
        "total_invested": config["initial_capital"] + total_contributions,
        "final_value": float(pv.iloc[-1]),
        "total_growth": float(pv.iloc[-1])
        - config["initial_capital"]
        - total_contributions,
    }

    weight_cols = [c for c in results.columns if c.endswith("_weight")]
    for col in weight_cols:
        ticker = col.replace("_weight", "")
        summary[f"{ticker}_avg_weight"] = float(results[col].mean())

    if benchmark is not None:
        benchmark = benchmark.reindex(pv.index).dropna()
        summary["benchmark_cagr"] = cagr(benchmark)
        summary["benchmark_sharpe"] = sharpe(benchmark, risk_free_rate)

    return summary


def _total_contributions(
    index: pd.DatetimeIndex, contribution_cfg: dict | None
) -> float:
    """Estimate total cash contributed over the backtest period.

    Args:
        index: Date index of the backtest results.
        contribution_cfg: The 'contribution' sub-dict from config, or None.

    Returns:
        Total dollars contributed (excluding initial capital).
    """
    if not contribution_cfg or not contribution_cfg.get("frequency"):
        return 0.0

    amount = contribution_cfg["amount"]
    frequency = contribution_cfg["frequency"]
    start, end = index[0], index[-1]

    if frequency == "M":
        periods = (end.year - start.year) * 12 + (end.month - start.month)
    elif frequency == "Q":
        start_q = start.year * 4 + (start.month - 1) // 3
        end_q = end.year * 4 + (end.month - 1) // 3
        periods = end_q - start_q
    else:
        return 0.0

    return max(periods, 0) * amount

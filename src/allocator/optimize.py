import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROLLING_WINDOW_DAYS = 504  # 2 years of trading days


def compute_weights(
    returns: pd.DataFrame,
    objective: str,
    risk_free_rate: float = 0.0,
    bounds: list[tuple[float, float]] | None = None,
) -> np.ndarray:
    """Compute target portfolio weights from historical returns.

    Args:
        returns: DataFrame of daily returns, one column per asset.
        objective: One of 'max_sharpe', 'min_vol', or 'equal_weight'.
        risk_free_rate: Annualized risk-free rate used in Sharpe calculation.
        bounds: Per-asset (min, max) weight bounds passed to the optimizer.
            When None, long-only with no upper cap is assumed.

    Returns:
        1-D array of weights aligned to returns.columns order, summing to 1.

    Raises:
        ValueError: If objective is not recognized.
    """
    n = len(returns.columns)

    if objective == "equal_weight":
        return np.full(n, 1.0 / n)

    window = returns.iloc[-ROLLING_WINDOW_DAYS:]
    mean_returns = window.mean()
    cov = window.cov()

    w0 = np.full(n, 1.0 / n)

    if objective == "max_sharpe":
        excess = (mean_returns - risk_free_rate / 252).values

        if bounds is None:
            # Sharpe ratio trick: fix w @ (mu - rf) = 1, minimize variance.
            # This converts the fractional Sharpe objective into a pure quadratic,
            # which is better conditioned than minimizing -Sharpe directly.
            # y is an auxiliary variable; normalize y / y.sum() to recover weights.
            # Requires unconstrained upside on y -- do not apply weight bounds here.
            def portfolio_variance(y):
                return y @ cov.values @ y

            result = minimize(
                portfolio_variance,
                w0,
                method="SLSQP",
                bounds=[(0.0, None)] * n,
                constraints=[{"type": "eq", "fun": lambda y: np.dot(y, excess) - 1.0}],
            )
            result.x = result.x / result.x.sum()
        else:
            # Sharpe trick breaks with per-asset bounds since y != w.
            # Minimize -Sharpe directly with the actual weight bounds instead.
            def neg_sharpe(w):
                port_return = np.dot(w, mean_returns) * 252
                port_vol = np.sqrt(w @ cov.values @ w * 252)
                return -(port_return - risk_free_rate) / port_vol

            result = minimize(
                neg_sharpe,
                w0,
                method="SLSQP",
                bounds=bounds,
                constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
            )

    elif objective == "min_vol":
        if bounds is not None:
            # Closed-form does not support bounds -- fall back to SLSQP.
            def portfolio_variance(w):
                return w @ cov.values @ w

            result = minimize(
                portfolio_variance,
                w0,
                method="SLSQP",
                bounds=bounds,
                constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0}],
            )
        else:
            # Closed-form minimum variance: w* = Sigma^-1 @ 1 / (1^T @ Sigma^-1 @ 1)
            # More numerically reliable than SLSQP on the variance objective directly.
            # Clamp negatives from floating point errors then re-normalize for long-only.
            cov_inv = np.linalg.inv(cov.values)
            ones = np.ones(n)
            raw_w = cov_inv @ ones / (ones @ cov_inv @ ones)
            raw_w = np.clip(raw_w, 0.0, None)
            return raw_w / raw_w.sum()

    else:
        raise ValueError(
            f"Unknown objective '{objective}'. "
            "Use 'max_sharpe', 'min_vol', or 'equal_weight'."
        )

    return result.x


if __name__ == "__main__":
    from data import fetch_prices

    prices = fetch_prices(["SPY", "TLT", "GLD", "QQQ"], "2015-01-01")
    returns = prices.pct_change().dropna()

    for obj in ("max_sharpe", "min_vol", "equal_weight"):
        weights = compute_weights(returns, obj)
        print(f"\n{obj}:")
        for ticker, w in zip(prices.columns, weights):
            print(f"  {ticker}: {w:.4f}")

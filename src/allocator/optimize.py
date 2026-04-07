import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROLLING_WINDOW_DAYS = 504  # 2 years of trading days


def compute_weights(
    returns: pd.DataFrame, objective: str, risk_free_rate: float = 0.0
) -> np.ndarray:
    """Compute target portfolio weights from historical returns.

    Args:
        returns: DataFrame of daily returns, one column per asset.
        objective: One of 'max_sharpe', 'min_vol', or 'equal_weight'.
        risk_free_rate: Annualized risk-free rate used in Sharpe calculation.

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
        # Sharpe ratio trick: fix w @ (mu - rf) = 1, minimize variance.
        # This converts the fractional Sharpe objective into a pure quadratic,
        # which is better conditioned than minimizing -Sharpe directly.
        # After solving, normalize y to sum to 1 to recover true weights.
        excess = (mean_returns - risk_free_rate / 252).values

        def portfolio_variance(y):
            return y @ cov.values @ y

        sharpe_constraints = [
            {"type": "eq", "fun": lambda y: np.dot(y, excess) - 1.0},
        ]
        sharpe_bounds = [(0.0, None)] * n

        result = minimize(
            portfolio_variance,
            w0,
            method="SLSQP",
            bounds=sharpe_bounds,
            constraints=sharpe_constraints,
        )
        result.x = result.x / result.x.sum()

    elif objective == "min_vol":
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

import numpy as np
import pandas as pd


def _apply_contribution(
    shares: np.ndarray,
    prices: pd.Series,
    portfolio_value: float,
    targets: np.ndarray,
    contribution_cfg: dict,
) -> np.ndarray:
    """Buy shares with a periodic cash contribution.

    Args:
        shares: Current share counts as a 1-D array.
        prices: Current price for each asset, aligned to shares.
        portfolio_value: Total portfolio value before the contribution.
        targets: Target weights as a 1-D array.
        contribution_cfg: The 'contribution' sub-dict from config.

    Returns:
        Updated share counts as a 1-D array.

    Raises:
        ValueError: If contribution method is not recognized.
    """
    amount = contribution_cfg["amount"]
    method = contribution_cfg["method"]

    if method == "smart":
        current_weights = (shares * prices.values) / portfolio_value
        underweight = targets - current_weights
        target_idx = int(np.argmax(underweight))
        new_shares = shares.copy()
        new_shares[target_idx] += amount / prices.iloc[target_idx]

    elif method == "pro_rata":
        new_shares = shares.copy()
        new_shares += (targets * amount) / prices.values

    else:
        raise ValueError(
            f"Unknown contribution method '{method}'. Use 'smart' or 'pro_rata'."
        )

    return new_shares

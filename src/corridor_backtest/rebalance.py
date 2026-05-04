import numpy as np
import pandas as pd


def _bands(targets: np.ndarray, band: float, threshold_type: str):
    """Return (lower, upper) bound arrays for each asset.

    Args:
        targets: Target weights as a 1-D array.
        band: Band width as a fraction.
        threshold_type: 'absolute' or 'relative'.

    Returns:
        Tuple of (lower, upper) 1-D arrays.

    Raises:
        ValueError: If threshold_type is not recognized.
    """
    if threshold_type == "absolute":
        return targets - band, targets + band
    elif threshold_type == "relative":
        return targets * (1 - band), targets * (1 + band)
    else:
        raise ValueError(
            f"Unknown threshold_type '{threshold_type}'. Use 'absolute' or 'relative'."
        )


def _breached(
    weights: np.ndarray, targets: np.ndarray, band: float, threshold_type: str
) -> bool:
    """Return True if any weight falls outside its corridor band.

    Args:
        weights: Current portfolio weights as a 1-D array.
        targets: Target weights as a 1-D array.
        band: Band width as a fraction.
        threshold_type: 'absolute' or 'relative'.

    Returns:
        True if any asset weight is outside [lower, upper].
    """
    lower, upper = _bands(targets, band, threshold_type)
    return bool(np.any(weights < lower) or np.any(weights > upper))


def _on_schedule(
    date: pd.Timestamp, schedule: str, last_rebalance: pd.Timestamp | None
) -> bool:
    """Return True if date falls in a new period relative to last_rebalance.

    Args:
        date: Current trading date.
        schedule: 'M' for monthly or 'Q' for quarterly.
        last_rebalance: Date of the most recent rebalance, or None if never rebalanced.

    Returns:
        True if a scheduled rebalance should fire on this date.

    Raises:
        ValueError: If schedule is not recognized.
    """
    if last_rebalance is None:
        return True
    if schedule == "M":
        return (date.year, date.month) > (last_rebalance.year, last_rebalance.month)
    if schedule == "Q":
        return (date.year, date.quarter) > (last_rebalance.year, last_rebalance.quarter)
    raise ValueError(f"Unknown schedule '{schedule}'. Use 'M' or 'Q'.")


def should_rebalance(
    date: pd.Timestamp,
    weights: np.ndarray,
    targets: np.ndarray,
    rebalance_cfg: dict,
    last_rebalance: pd.Timestamp | None,
    breach_since_last: bool,
) -> tuple[bool, str]:
    """Decide whether to rebalance on the given date.

    Args:
        date: Current trading date.
        weights: Current portfolio weights as a 1-D array.
        targets: Target weights as a 1-D array.
        rebalance_cfg: The 'rebalance' sub-dict from config.
        last_rebalance: Date of the most recent rebalance, or None.
        breach_since_last: True if a corridor breach occurred since the last rebalance.
            Only relevant for hybrid mode.

    Returns:
        Tuple of (do_rebalance, trigger_type) where trigger_type is one of
        'periodic', 'corridor', 'hybrid', or '' (no rebalance).

    Raises:
        ValueError: If mode is not recognized.
    """
    mode = rebalance_cfg["mode"]
    band = rebalance_cfg["band"]
    trigger_band = rebalance_cfg.get("corridor", band)
    threshold_type = rebalance_cfg["threshold_type"]
    schedule = rebalance_cfg.get("schedule", "Q")

    if mode == "none":
        return False, ""

    if mode == "periodic":
        if _on_schedule(date, schedule, last_rebalance):
            return True, "periodic"
        return False, ""

    if mode == "corridor":
        if _breached(weights, targets, trigger_band, threshold_type):
            return True, "corridor"
        return False, ""

    if mode == "hybrid":
        if _on_schedule(date, schedule, last_rebalance) and breach_since_last:
            return True, "hybrid"
        return False, ""

    raise ValueError(
        f"Unknown rebalance mode '{mode}'. "
        "Use 'none', 'periodic', 'corridor', or 'hybrid'."
    )


def apply_rebalance(
    portfolio_value: float,
    targets: np.ndarray,
    prices: pd.Series,
    current_weights: np.ndarray,
    rebalance_cfg: dict,
) -> tuple[np.ndarray, float]:
    """Compute share counts after a rebalance event, net of transaction costs.

    Transaction cost is modelled as a flat round-trip rate applied to
    one-sided turnover: cost = portfolio_value * turnover * cost_bps / 10_000.
    The cost is deducted from portfolio value before shares are allocated, so
    it flows through naturally to all downstream metrics.

    Args:
        portfolio_value: Total portfolio value in dollars.
        targets: Target weight for each asset, summing to 1.
        prices: Current price for each asset, index aligned to targets.
        current_weights: Actual weights just before rebalancing.
        rebalance_cfg: The 'rebalance' sub-dict from config.

    Returns:
        Tuple of (shares, cost_dollars) where shares is a 1-D array of share
        counts aligned to prices.index order and cost_dollars is the dollar
        value consumed by transaction costs on this rebalance.

    Raises:
        ValueError: If rebalance_to is not recognized.
    """
    rebalance_to = rebalance_cfg.get("rebalance_to", "target")

    if rebalance_to == "target":
        final_weights = targets

    elif rebalance_to == "band_edge":
        band = rebalance_cfg["band"]
        threshold_type = rebalance_cfg["threshold_type"]
        lower, upper = _bands(targets, band, threshold_type)

        final_weights = current_weights.copy()
        final_weights = np.where(current_weights < lower, lower, final_weights)
        final_weights = np.where(current_weights > upper, upper, final_weights)
        final_weights = final_weights / final_weights.sum()

    else:
        raise ValueError(
            f"Unknown rebalance_to '{rebalance_to}'. Use 'target' or 'band_edge'."
        )

    cost_bps = rebalance_cfg.get("transaction_cost_bps", 0.0)
    one_sided_turnover = float(np.sum(np.abs(final_weights - current_weights)) / 2)
    cost_dollars = portfolio_value * one_sided_turnover * cost_bps / 10_000

    net_value = portfolio_value - cost_dollars
    dollar_allocations = final_weights * net_value
    return dollar_allocations / prices.values, cost_dollars

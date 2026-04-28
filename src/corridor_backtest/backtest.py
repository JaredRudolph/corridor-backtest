import numpy as np
import pandas as pd

from corridor_backtest.optimize import compute_weights
from corridor_backtest.rebalance import _breached, _on_schedule, apply_rebalance, should_rebalance


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


def _contribution_due(
    date: pd.Timestamp, frequency: str, last_contribution: pd.Timestamp
) -> bool:
    """Return True if a contribution should fire on this date.

    Args:
        date: Current trading date.
        frequency: 'M' for monthly or 'Q' for quarterly.
        last_contribution: Date of the most recent contribution.

    Returns:
        True if date falls in a new period relative to last_contribution.

    Raises:
        ValueError: If frequency is not recognized.
    """
    if frequency == "M":
        return (date.year, date.month) > (
            last_contribution.year,
            last_contribution.month,
        )
    if frequency == "Q":
        return (date.year, date.quarter) > (
            last_contribution.year,
            last_contribution.quarter,
        )
    raise ValueError(f"Unknown contribution frequency '{frequency}'. Use 'M' or 'Q'.")


def _resolve_bounds(
    optimize_cfg: dict,
    initial_weights: dict,
    tickers: list[str],
) -> list[tuple[float, float]]:
    """Resolve weight_bounds from the optimize config into a per-asset list.

    Args:
        optimize_cfg: The 'optimize' sub-dict from config.
        initial_weights: Ticker-to-weight mapping from the portfolio config.
        tickers: Ordered list of tickers matching prices.columns.

    Returns:
        List of (min, max) tuples aligned to tickers order.

    Raises:
        KeyError: If per-asset bounds are missing a ticker.
        ValueError: If weight_bounds format is not recognized.
    """
    weight_bounds = optimize_cfg.get("weight_bounds")

    if weight_bounds is None:
        return [(0.0, None)] * len(tickers)

    if "min" in weight_bounds and "max" in weight_bounds:
        lo_mult = weight_bounds["min"]
        hi_mult = weight_bounds["max"]
        return [
            (initial_weights[t] * lo_mult, initial_weights[t] * hi_mult)
            for t in tickers
        ]

    # Per-asset bounds dict.
    missing = [t for t in tickers if t not in weight_bounds]
    if missing:
        raise KeyError(
            f"weight_bounds is missing entries for: {missing}. "
            "Provide bounds for every ticker or use a lazy global dict."
        )
    return [(weight_bounds[t][0], weight_bounds[t][1]) for t in tickers]


def run_backtest(
    prices: pd.DataFrame, config: dict
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run a single portfolio backtest over the provided price history.

    Args:
        prices: DataFrame of adjusted close prices, date-indexed, one column per ticker.
        config: A single portfolio config dict.

    Returns:
        Tuple of (results, rebalance_log) where:
          - results: date-indexed DataFrame with portfolio_value, per-asset weights,
            rebalanced flag, and trigger type.
          - rebalance_log: DataFrame with one row per rebalance event, including
            pre- and post-rebalance weights. Empty DataFrame if no events occurred.

    Raises:
        KeyError: If any config ticker is missing from prices.
    """
    tickers = config["tickers"]
    missing = [t for t in tickers if t not in prices.columns]
    if missing:
        raise KeyError(f"Tickers not found in price data: {missing}")

    prices = prices[tickers]
    returns = prices.pct_change().dropna()

    initial_weights_dict = config["weights"]
    targets = np.array([initial_weights_dict[t] for t in tickers])

    optimize_cfg = config.get("optimize")
    bounds = (
        _resolve_bounds(optimize_cfg, initial_weights_dict, tickers)
        if optimize_cfg
        else None
    )

    rebalance_cfg = config["rebalance"]
    contribution_cfg = config.get("contribution")
    risk_free_rate = config.get("risk_free_rate", 0.0)

    shares = targets * config["initial_capital"] / prices.iloc[0].values
    last_rebalance = prices.index[0]
    last_contribution = prices.index[0]
    last_opt_update = prices.index[0]
    breach_since_last = False

    records = []
    rebalance_log = []

    for date in prices.index:
        price_row = prices.loc[date]

        if contribution_cfg and contribution_cfg.get("frequency"):
            if _contribution_due(
                date, contribution_cfg["frequency"], last_contribution
            ):
                port_val = float(shares @ price_row.values)
                shares = _apply_contribution(
                    shares, price_row, port_val, targets, contribution_cfg
                )
                last_contribution = date

        port_val = float(shares @ price_row.values)
        current_weights = (shares * price_row.values) / port_val

        if rebalance_cfg["mode"] == "hybrid":
            trigger_band = rebalance_cfg.get("corridor", rebalance_cfg["band"])
            if _breached(
                current_weights,
                targets,
                trigger_band,
                rebalance_cfg["threshold_type"],
            ):
                breach_since_last = True

        do_rebalance, trigger = should_rebalance(
            date,
            current_weights,
            targets,
            rebalance_cfg,
            last_rebalance,
            breach_since_last,
        )

        if do_rebalance:
            pre_weights = current_weights.copy()

            if optimize_cfg and date in returns.index:
                opt_schedule = rebalance_cfg.get("schedule", "Q")
                if _on_schedule(date, opt_schedule, last_opt_update):
                    targets = compute_weights(
                        returns.loc[:date],
                        optimize_cfg["objective"],
                        risk_free_rate,
                        bounds,
                    )
                    last_opt_update = date

            shares = apply_rebalance(
                port_val, targets, price_row, current_weights, rebalance_cfg
            )
            post_weights = (shares * price_row.values) / port_val

            rebalance_log.append(
                {
                    "date": date,
                    "trigger": trigger,
                    **{f"{t}_pre": pre_weights[i] for i, t in enumerate(tickers)},
                    **{f"{t}_post": post_weights[i] for i, t in enumerate(tickers)},
                }
            )

            last_rebalance = date
            breach_since_last = False

        records.append(
            {
                "date": date,
                "portfolio_value": port_val,
                **{f"{t}_weight": current_weights[i] for i, t in enumerate(tickers)},
                **{f"{t}_target": targets[i] for i, t in enumerate(tickers)},
                "rebalanced": do_rebalance,
                "trigger": trigger,
            }
        )

    results = pd.DataFrame(records).set_index("date")
    log = (
        pd.DataFrame(rebalance_log).set_index("date")
        if rebalance_log
        else pd.DataFrame()
    )

    return results, log

portfolios = [
    # --- Group 1: rebalancing mode comparison ---
    # Same risk-parity allocation across three rebalancing modes.
    # Isolates the effect of corridor vs periodic vs none on identical holdings.
    {
        "name": "rp_corridor",
        "tickers": ["SPY", "TLT", "GLD", "IEF"],
        "weights": {"SPY": 0.30, "TLT": 0.40, "GLD": 0.15, "IEF": 0.15},
        "benchmark": "SPY",
        "start": "2015-01-01",
        "end": None,
        "initial_capital": 10_000,
        "risk_free_rate": 0.0,
        "contribution": {
            "amount": 500,
            "frequency": "M",
            "method": "smart",
        },
        "rebalance": {
            "mode": "corridor",
            "threshold_type": "relative",
            "band": 0.15,
            "rebalance_to": "target",
            "schedule": "Q",
        },
    },
    {
        "name": "rp_periodic",
        "tickers": ["SPY", "TLT", "GLD", "IEF"],
        "weights": {"SPY": 0.30, "TLT": 0.40, "GLD": 0.15, "IEF": 0.15},
        "benchmark": "SPY",
        "start": "2015-01-01",
        "end": None,
        "initial_capital": 10_000,
        "risk_free_rate": 0.0,
        "contribution": {
            "amount": 500,
            "frequency": "M",
            "method": "smart",
        },
        "rebalance": {
            "mode": "periodic",
            "threshold_type": "relative",
            "band": 0.15,
            "rebalance_to": "target",
            "schedule": "Q",
        },
    },
    {
        "name": "rp_hold",
        "tickers": ["SPY", "TLT", "GLD", "IEF"],
        "weights": {"SPY": 0.30, "TLT": 0.40, "GLD": 0.15, "IEF": 0.15},
        "benchmark": "SPY",
        "start": "2015-01-01",
        "end": None,
        "initial_capital": 10_000,
        "risk_free_rate": 0.0,
        "contribution": {
            "amount": 500,
            "frequency": "M",
            "method": "pro_rata",
        },
        "rebalance": {
            "mode": "none",
            "threshold_type": "relative",
            "band": 0.15,
            "rebalance_to": "target",
            "schedule": "Q",
        },
    },
    # --- Group 2: leveraged risk parity ---
    # 3x leveraged equity and bond ETFs with gold. High volatility means corridor
    # bands trigger frequently -- the clearest demonstration of corridor behavior.
    # Band search finds the width that best balances Calmar under high-drift conditions.
    {
        "name": "leveraged_rp",
        "tickers": ["UPRO", "TMF", "GLD"],
        "weights": {"UPRO": 0.40, "TMF": 0.40, "GLD": 0.20},
        "benchmark": "SPY",
        "start": "2015-01-01",
        "end": None,
        "initial_capital": 10_000,
        "risk_free_rate": 0.0,
        "contribution": {
            "amount": 500,
            "frequency": "M",
            "method": "smart",
        },
        "rebalance": {
            "mode": "corridor",
            "threshold_type": "absolute",
            "band": 0.08,
            "rebalance_to": "target",
            "schedule": "Q",
        },
        "band_search": {
            "metric": "calmar",
            "band_range": [0.02, 0.20],
            "steps": 20,
        },
    },
    # --- Group 3: conservative, regime-balanced ---
    # Ray Dalio All Weather: designed to hold through any economic regime.
    # Hybrid mode rebalances on schedule only when drift has already occurred,
    # matching how a low-turnover institutional strategy would be managed.
    {
        "name": "all_weather",
        "tickers": ["SPY", "TLT", "IEF", "GLD", "DBC"],
        "weights": {"SPY": 0.30, "TLT": 0.40, "IEF": 0.15, "GLD": 0.075, "DBC": 0.075},
        "benchmark": "SPY",
        "start": "2015-01-01",
        "end": None,
        "initial_capital": 10_000,
        "risk_free_rate": 0.0,
        "contribution": {
            "amount": 500,
            "frequency": "M",
            "method": "smart",
        },
        "rebalance": {
            "mode": "hybrid",
            "threshold_type": "absolute",
            "band": 0.05,
            "rebalance_to": "target",
            "schedule": "Q",
        },
    },
    # --- Group 3b: mixed leveraged / unleveraged ---
    # 50% leveraged (UPRO/TMF/TECL) + 50% unleveraged (SPY/XLK). Corridor rebalancing
    # systematically trims leveraged winners into the unleveraged side and buys back
    # when leveraged positions drop. Absolute bands suit the high-vol leveraged
    # positions.
    {
        "name": "lev_unlev_mix",
        "tickers": ["UPRO", "TMF", "TECL", "SPY", "XLK"],
        "weights": {"UPRO": 0.20, "TMF": 0.15, "TECL": 0.15, "SPY": 0.30, "XLK": 0.20},
        "benchmark": "SPY",
        "start": "2015-01-01",
        "end": None,
        "initial_capital": 10_000,
        "risk_free_rate": 0.0,
        "contribution": {
            "amount": 500,
            "frequency": "M",
            "method": "smart",
        },
        "rebalance": {
            "mode": "corridor",
            "threshold_type": "absolute",
            "band": 0.07,
            "rebalance_to": "target",
            "schedule": "Q",
        },
        "band_search": {
            "metric": "calmar",
            "band_range": [0.02, 0.20],
            "steps": 20,
        },
    },
    # --- Group 4: optimized corridor ---
    # Global diversified equity and bonds with a rolling max-Sharpe optimizer.
    # Band search finds the corridor width that maximizes Sharpe over the backtest.
    # Shows how corridor + optimization interact on a multi-asset growth portfolio.
    {
        "name": "global_sharpe",
        "tickers": ["SPY", "QQQ", "EFA", "EEM", "TLT"],
        "weights": {"SPY": 0.35, "QQQ": 0.20, "EFA": 0.20, "EEM": 0.10, "TLT": 0.15},
        "benchmark": "SPY",
        "start": "2015-01-01",
        "end": None,
        "initial_capital": 10_000,
        "risk_free_rate": 0.0,
        "contribution": {
            "amount": 500,
            "frequency": "M",
            "method": "smart",
        },
        "rebalance": {
            "mode": "corridor",
            "threshold_type": "relative",
            "band": 0.10,
            "rebalance_to": "target",
            "schedule": "Q",
        },
        "optimize": {
            "objective": "max_sharpe",
            "weight_bounds": {
                "SPY": [0.15, 0.55],
                "QQQ": [0.05, 0.40],
                "EFA": [0.05, 0.35],
                "EEM": [0.02, 0.25],
                "TLT": [0.05, 0.30],
            },
        },
        "band_search": {
            "metric": "sharpe",
            "band_range": [0.02, 0.25],
            "steps": 20,
        },
    },
]

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
            "transaction_cost_bps": 5,
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
            "transaction_cost_bps": 5,
        },
    },
    # --- Group 2: leveraged risk parity ---
    # 3x leveraged equity and bond ETFs with gold. Hybrid mode gates rebalancing to the
    # quarterly schedule while tracking corridor breaches daily -- prevents chattering
    # from band_edge + high-volatility drift. Band search optimizes the corridor width.
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
            "band": 0.05,
            "corridor": 0.15,
            "rebalance_to": "band_edge",
            "schedule": "Q",
            "transaction_cost_bps": 10,
        },
        "band_search": {
            "metric": "calmar",
            "band_range": [0.02, 0.20],
            "corridor_range": [0.04, 0.25],
            "steps": 10,
            "train_frac": 0.7,
            "robustness_threshold": 0.95,
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
            "transaction_cost_bps": 5,
        },
    },
    # --- Group 5: leveraged ETF corridor strategies (band_edge) ---
    # All four use band_edge rebalancing: trades only as far as needed to exit the
    # breach, reducing turnover friction on high-volatility leveraged instruments.
    #
    # hfea: canonical Hedgefundie 55/45 UPRO/TMF. Baseline for the group.
    {
        "name": "hfea",
        "tickers": ["UPRO", "TMF"],
        "weights": {"UPRO": 0.55, "TMF": 0.45},
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
            "band": 0.05,
            "corridor": 0.15,
            "rebalance_to": "band_edge",
            "schedule": "Q",
            "transaction_cost_bps": 10,
        },
        "band_search": {
            "metric": "calmar",
            "band_range": [0.02, 0.20],
            "corridor_range": [0.04, 0.25],
            "steps": 10,
            "train_frac": 0.7,
            "robustness_threshold": 0.95,
        },
    },
    # hfea_blended: HFEA variant splitting the bond leg equally between TYD (3x 7-10yr)
    # and TMF (3x 20+yr). Blending duration reduces sensitivity to long-end rate moves
    # while preserving the levered bond hedge. Compares directly against hfea above.
    {
        "name": "hfea_blended",
        "tickers": ["UPRO", "TYD", "TMF"],
        "weights": {"UPRO": 0.55, "TYD": 0.225, "TMF": 0.225},
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
            "band": 0.05,
            "corridor": 0.15,
            "rebalance_to": "band_edge",
            "schedule": "Q",
            "transaction_cost_bps": 10,
        },
        "band_search": {
            "metric": "calmar",
            "band_range": [0.02, 0.20],
            "corridor_range": [0.04, 0.25],
            "steps": 10,
            "train_frac": 0.7,
            "robustness_threshold": 0.95,
        },
    },
    # lev_sector: four-asset leveraged portfolio adding tech-sector concentration via
    # TECL
    # (3x XLK). Broader equity diversity across market cap and sector, all at 3x. Wider
    # band search range accounts for higher multi-asset drift variance.
    {
        "name": "lev_sector",
        "tickers": ["UPRO", "TQQQ", "TECL", "TMF"],
        "weights": {"UPRO": 0.25, "TQQQ": 0.25, "TECL": 0.20, "TMF": 0.30},
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
            "band": 0.06,
            "corridor": 0.16,
            "rebalance_to": "band_edge",
            "schedule": "Q",
            "transaction_cost_bps": 10,
        },
        "band_search": {
            "metric": "calmar",
            "band_range": [0.02, 0.20],
            "corridor_range": [0.04, 0.28],
            "steps": 10,
            "train_frac": 0.7,
            "robustness_threshold": 0.95,
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
            "transaction_cost_bps": 5,
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
            "train_frac": 0.7,
            "robustness_threshold": 0.95,
        },
    },
]

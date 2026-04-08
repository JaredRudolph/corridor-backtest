portfolios = [
    {
        "name": "corridor_relative",
        "tickers": ["SPY", "TLT", "GLD", "QQQ"],
        "weights": {"SPY": 0.40, "TLT": 0.30, "GLD": 0.15, "QQQ": 0.15},
        "benchmark": "SPY",
        "start": "2015-01-01",
        "end": None,  # None defaults to today
        "initial_capital": 10_000,
        "risk_free_rate": 0.0,
        "contribution": {
            "amount": 500,
            "frequency": "M",  # M | Q | None
            "method": "smart",  # smart | pro_rata
        },
        "rebalance": {
            "mode": "corridor",  # none | periodic | corridor | hybrid
            "threshold_type": "relative",  # absolute | relative
            "band": 0.10,
            "rebalance_to": "target",  # target | band_edge
            "schedule": "Q",  # used if mode is periodic or hybrid
        },
        "optimize": {  # omit this key entirely to use fixed weights
            "objective": "max_sharpe",  # max_sharpe | min_vol | equal_weight
            "weight_bounds": {  # per-asset bounds
                "SPY": [0.10, 0.60],
                "TLT": [0.05, 0.45],
                "GLD": [0.05, 0.30],
                "QQQ": [0.05, 0.30],
            },
            # lazy global alternative:
            #   multipliers on initial weights, scales with allocation:
            # "weight_bounds": {"min": 0.25, "max": 1.75},
        },
        "band_search": {  # omit this key to skip parameter search
            "metric": "sharpe",  # sharpe | cagr | calmar | sortino
            "band_range": [0.02, 0.25],
            "steps": 20,
        },
    },
    {
        "name": "periodic_minvol",
        "tickers": ["SPY", "TLT", "GLD", "QQQ"],
        "weights": {"SPY": 0.40, "TLT": 0.30, "GLD": 0.15, "QQQ": 0.15},
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
            "band": 0.10,
            "rebalance_to": "target",
            "schedule": "Q",
        },
        "optimize": {
            "objective": "min_vol",
            "weight_bounds": {
                "SPY": [0.10, 0.60],
                "TLT": [0.05, 0.45],
                "GLD": [0.05, 0.30],
                "QQQ": [0.05, 0.30],
            },
        },
    },
    {
        "name": "buy_and_hold",
        "tickers": ["SPY", "TLT", "GLD", "QQQ"],
        "weights": {"SPY": 0.40, "TLT": 0.30, "GLD": 0.15, "QQQ": 0.15},
        "benchmark": "SPY",
        "start": "2015-01-01",
        "end": None,
        "initial_capital": 10_000,
        "risk_free_rate": 0.0,
        "contribution": {
            "amount": 500,
            "frequency": "M",
            "method": "pro_rata",  # no targets to chase, split by initial weights
        },
        "rebalance": {
            "mode": "none",
            "threshold_type": "relative",
            "band": 0.10,
            "rebalance_to": "target",
            "schedule": "Q",
        },
    },
]

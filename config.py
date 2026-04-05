config = {
    "tickers": ["SPY", "TLT", "GLD", "QQQ"],
    "benchmark": "SPY",
    "start": "2015-01-01",
    "end": None,
    "initial_capital": 10_000,
    "risk_free_rate": 0.0,
    "contribution": {
        "amount": 500,
        "frequency": "M",  # M | Q | None
        "method": "smart",  # smart | pro_rata
    },
    "rebalance": {
        "mode": "corridor",  # corridor | periodic | hybrid
        "threshold_type": "relative",  # absolute | relative
        "band": 0.10,
        "schedule": "Q",  # used for periodic and hybrid modes
    },
    "optimize": "max_sharpe",  # max_sharpe | min_vol | equal_weight
}

import pandas as pd
from loguru import logger

from corridor_backtest.backtest import run_backtest
from corridor_backtest.band_search import search_band
from corridor_backtest.data import fetch_prices
from corridor_backtest.metrics import summarize


def run_pipeline(
    portfolios: list[dict],
) -> tuple[pd.DataFrame, list[dict]]:
    """Run backtests for one or more portfolios and return a side-by-side comparison.

    For each portfolio:
      1. Fetches price history (including benchmark ticker).
      2. Runs band search if 'band_search' key is present, patching the best band
         into the rebalance config before the main backtest.
      3. Runs the backtest.
      4. Computes performance metrics against the portfolio and benchmark.

    Args:
        portfolios: List of portfolio config dicts.

    Returns:
        Tuple of (comparison, portfolio_data) where:
          - comparison: DataFrame with one row per portfolio and one column per metric.
          - portfolio_data: List of dicts, each containing 'name', 'results',
            and 'rebalance_log' for the corresponding portfolio.
    """
    summaries = []
    portfolio_data = []

    for config in portfolios:
        name = config["name"]
        logger.info(f"Running portfolio: {name}")

        tickers = config["tickers"]
        benchmark = config.get("benchmark")
        fetch_tickers = list(
            dict.fromkeys(tickers + ([benchmark] if benchmark else []))
        )

        prices = fetch_prices(fetch_tickers, config["start"], config.get("end"))
        portfolio_prices = prices[tickers]
        benchmark_prices = (
            prices[benchmark] if benchmark and benchmark in prices.columns else None
        )

        band_search_results = None
        if "band_search" in config:
            logger.info(
                f"[{name}] Running band search ({config['band_search']['metric']})..."
            )
            best_band, band_search_results = search_band(portfolio_prices, config)
            logger.info(
                f"[{name}] Best band: {best_band:.4f} "
                f"(score: {band_search_results.iloc[0]['score']:.4f})"
            )
            config = {**config, "rebalance": {**config["rebalance"], "band": best_band}}

        results, rebalance_log = run_backtest(portfolio_prices, config)

        summary = summarize(results, rebalance_log, config, benchmark_prices)
        summaries.append(summary)
        portfolio_data.append(
            {
                "name": name,
                "results": results,
                "rebalance_log": rebalance_log,
                "band_search_results": band_search_results,
                "config": config,
            }
        )

        logger.info(
            f"[{name}] CAGR: {summary['cagr']:.2%} | "
            f"Sharpe: {summary['sharpe']:.2f} | "
            f"Max DD: {summary['max_drawdown']:.2%}"
        )

    comparison = pd.DataFrame(summaries).set_index("name")
    return comparison, portfolio_data

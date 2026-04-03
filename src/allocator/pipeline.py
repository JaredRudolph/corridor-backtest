from pathlib import Path

from loguru import logger

from .backtest import run_backtest
from .data import fetch_prices
from .metrics import compute_metrics

OUTPUT_PATH = Path("data/processed/backtest_results.parquet")


def run_pipeline(cfg: dict) -> dict:
    """Fetch prices, run backtest, compute metrics, and save results.

    Returns a dict with keys: results, events, metrics.
    """
    logger.info("Starting pipeline")

    # Deduplicate while preserving order; benchmark may already be in tickers
    all_tickers = list(dict.fromkeys(cfg["tickers"] + [cfg["benchmark"]]))
    prices = fetch_prices(all_tickers, cfg["start"], cfg.get("end"))

    results, events = run_backtest(prices[cfg["tickers"]], cfg)

    benchmark_prices = prices[cfg["benchmark"]]
    metrics = compute_metrics(results, benchmark_prices, cfg, events)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_parquet(OUTPUT_PATH)
    logger.info(f"Results saved to {OUTPUT_PATH}")

    _log_summary(metrics)
    return {"results": results, "events": events, "metrics": metrics}


def _log_summary(metrics: dict) -> None:
    p = metrics["portfolio"]
    b = metrics["benchmark"]
    logger.info(
        f"Portfolio | CAGR: {p['cagr']:.2%}  Sharpe: {p['sharpe']:.2f}"
        f"  Max DD: {p['max_drawdown']:.2%}"
    )
    logger.info(
        f"Benchmark | CAGR: {b['cagr']:.2%}  Sharpe: {b['sharpe']:.2f}"
        f"  Max DD: {b['max_drawdown']:.2%}"
    )
    logger.info(
        f"Rebalances: {metrics['rebalance_events']}"
        f"  Contributions: ${metrics['total_contributions']:,.0f}"
        f"  Growth: ${metrics['growth']:,.0f}"
    )

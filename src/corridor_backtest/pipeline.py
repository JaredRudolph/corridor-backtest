import pandas as pd
from loguru import logger

from corridor_backtest.backtest import run_backtest
from corridor_backtest.band_search import search_band
from corridor_backtest.data import fetch_prices
from corridor_backtest.metrics import cagr, max_drawdown, sharpe, summarize


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

        train_end_date = None
        band_search_results = None
        if "band_search" in config:
            band_cfg = config["band_search"]
            train_frac = band_cfg.get("train_frac")
            search_prices = portfolio_prices
            if train_frac is not None:
                n = len(portfolio_prices)
                train_n = max(int(n * train_frac), 1)
                train_end_date = portfolio_prices.index[train_n - 1]
                search_prices = portfolio_prices.iloc[:train_n]
                logger.info(
                    f"[{name}] Band search train window: "
                    f"{search_prices.index[0].date()} to {train_end_date.date()} "
                    f"({train_frac:.0%} of data)"
                )

            logger.info(f"[{name}] Running band search ({band_cfg['metric']})...")
            best_params, band_search_results = search_band(search_prices, config)
            params_str = ", ".join(f"{k}={v:.4f}" for k, v in best_params.items())
            logger.info(
                f"[{name}] Best params: {params_str} "
                f"(score: {band_search_results.iloc[0]['score']:.4f})"
            )
            config = {**config, "rebalance": {**config["rebalance"], **best_params}}

        results, rebalance_log = run_backtest(portfolio_prices, config)

        summary = summarize(results, rebalance_log, config, benchmark_prices)

        if train_end_date is not None:
            pv = results["portfolio_value"]
            rfr = config.get("risk_free_rate", 0.0)
            train_pv = pv[pv.index <= train_end_date]
            test_pv = pv[pv.index > train_end_date]
            summary["train_cagr"] = (
                cagr(train_pv) if len(train_pv) > 1 else float("nan")
            )
            summary["train_sharpe"] = (
                sharpe(train_pv, rfr) if len(train_pv) > 1 else float("nan")
            )
            summary["train_max_drawdown"] = (
                max_drawdown(train_pv) if len(train_pv) > 1 else float("nan")
            )
            summary["test_cagr"] = cagr(test_pv) if len(test_pv) > 1 else float("nan")
            summary["test_sharpe"] = (
                sharpe(test_pv, rfr) if len(test_pv) > 1 else float("nan")
            )
            summary["test_max_drawdown"] = (
                max_drawdown(test_pv) if len(test_pv) > 1 else float("nan")
            )

        summaries.append(summary)
        portfolio_data.append(
            {
                "name": name,
                "results": results,
                "rebalance_log": rebalance_log,
                "band_search_results": band_search_results,
                "train_end_date": train_end_date,
                "config": config,
            }
        )

        logger.info(
            f"[{name}] CAGR: {summary['cagr']:.2%} | "
            f"Sharpe: {summary['sharpe']:.2f} | "
            f"Max DD: {summary['max_drawdown']:.2%}"
        )
        if train_end_date is not None:
            t_sharpe = summary.get("train_sharpe", float("nan"))
            v_sharpe = summary.get("test_sharpe", float("nan"))
            t_cagr = summary.get("train_cagr", float("nan"))
            v_cagr = summary.get("test_cagr", float("nan"))
            logger.info(
                f"[{name}] Train/test -- "
                f"Sharpe: {t_sharpe:.2f} / {v_sharpe:.2f} "
                f"(gap {t_sharpe - v_sharpe:+.2f}) | "
                f"CAGR: {t_cagr:.2%} / {v_cagr:.2%} (gap {t_cagr - v_cagr:+.2%})"
            )

    comparison = pd.DataFrame(summaries).set_index("name")
    return comparison, portfolio_data

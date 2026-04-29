from pathlib import Path

from loguru import logger

from config import portfolios
from corridor_backtest.data import fetch_prices
from corridor_backtest.pipeline import run_pipeline
from corridor_backtest.plots import plot_corridor_dashboard, plot_dashboard

OUTPUT_DIR = Path("data/processed")
PLOTS_DIR = OUTPUT_DIR / "plots"
ASSETS_DIR = Path("assets")


def main() -> None:
    logger.info(f"Starting backtest for {len(portfolios)} portfolio(s).")

    comparison, portfolio_data = run_pipeline(portfolios)

    print("\n--- Portfolio Comparison ---")
    print(comparison.T.to_string())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    for entry in portfolio_data:
        name = entry["name"]
        entry["results"].to_parquet(OUTPUT_DIR / f"{name}_results.parquet")
        if not entry["rebalance_log"].empty:
            entry["rebalance_log"].to_parquet(
                OUTPUT_DIR / f"{name}_rebalance_log.parquet"
            )

    benchmark_ticker = portfolios[0].get("benchmark")
    benchmark = None
    if benchmark_ticker:
        prices = fetch_prices(
            [benchmark_ticker],
            portfolios[0]["start"],
            portfolios[0].get("end"),
        )
        benchmark = prices[benchmark_ticker]

    dashboard_path = str(PLOTS_DIR / "dashboard.png")
    assets_path = str(ASSETS_DIR / "dashboard.png")
    plot_dashboard(
        comparison,
        portfolio_data,
        benchmark=benchmark,
        output_path=dashboard_path,
    )
    plot_dashboard(
        comparison,
        portfolio_data,
        benchmark=benchmark,
        output_path=assets_path,
    )
    logger.info(f"Dashboard saved to {dashboard_path} and {assets_path}")

    corridor_path = str(PLOTS_DIR / "summary_dashboard.png")
    corridor_assets_path = str(ASSETS_DIR / "summary_dashboard.png")
    plot_corridor_dashboard(portfolio_data, output_path=corridor_path)
    plot_corridor_dashboard(portfolio_data, output_path=corridor_assets_path)
    logger.info(f"Summary dashboard saved to {corridor_path} and {corridor_assets_path}")

    logger.info(f"Results saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

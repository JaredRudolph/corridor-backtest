from pathlib import Path

from loguru import logger

from allocator.pipeline import run_pipeline
from config import portfolios

OUTPUT_DIR = Path("data/processed")


def main() -> None:
    logger.info(f"Starting backtest for {len(portfolios)} portfolio(s).")

    comparison, portfolio_data = run_pipeline(portfolios)

    print("\n--- Portfolio Comparison ---")
    print(comparison.T.to_string())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for entry in portfolio_data:
        name = entry["name"]
        entry["results"].to_parquet(OUTPUT_DIR / f"{name}_results.parquet")
        if not entry["rebalance_log"].empty:
            entry["rebalance_log"].to_parquet(
                OUTPUT_DIR / f"{name}_rebalance_log.parquet"
            )

    logger.info(f"Results saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

import pandas as pd
import yfinance as yf
from loguru import logger


def fetch_prices(
    tickers: list[str], start: str, end: str | None = None
) -> pd.DataFrame:
    """Download adjusted close prices for tickers, inner-joined on date index.

    Args:
        tickers: List of ticker symbols.
        start: Start date string (YYYY-MM-DD).
        end: End date string (YYYY-MM-DD), or None for today.

    Returns:
        DataFrame of adjusted close prices with date index and ticker columns.

    Raises:
        ValueError: If no price data is returned for any ticker.
    """
    logger.info(f"Fetching prices for {tickers} from {start} to {end or 'today'}")

    raw = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
    )

    if raw.empty:
        raise ValueError(f"No price data returned for tickers: {tickers}")

    prices = raw["Close"]

    if isinstance(prices, pd.Series):
        prices = prices.to_frame(name=tickers[0])

    prices = prices[tickers]
    prices = prices.dropna(how="any")

    logger.info(
        f"Fetched {len(prices)} trading days ({prices.index[0].date()} to {prices.index[-1].date()})"  # noqa
    )

    return prices

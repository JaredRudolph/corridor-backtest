import pandas as pd
import yfinance as yf
from loguru import logger


def fetch_prices(tickers: list[str], start: str, end: str | None = None) -> pd.DataFrame:
    """Fetch adjusted close prices, inner-joined on date index.

    Rows with any missing ticker are dropped rather than forward-filled.
    """
    logger.info(f"Fetching {len(tickers)} tickers from {start} to {end or 'today'}")
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)

    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"].copy()
    else:
        # Single-ticker download returns flat columns
        prices = raw[["Close"]].rename(columns={"Close": tickers[0]})

    prices = prices[tickers].dropna(how="any")
    logger.info(f"Loaded {len(prices)} trading days")
    return prices

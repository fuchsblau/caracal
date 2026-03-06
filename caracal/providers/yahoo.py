"""Yahoo Finance market data provider."""

import logging
from datetime import date

import pandas as pd
import yfinance as yf

from caracal.providers.types import ProviderError, TickerNotFoundError

logger = logging.getLogger("caracal")

# Suppress noisy yfinance warnings (e.g. "possibly delisted")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)


class YahooProvider:
    """Fetch market data from Yahoo Finance via yfinance."""

    @property
    def name(self) -> str:
        return "yahoo"

    def fetch_ohlcv(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        try:
            df = yf.download(
                ticker,
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                progress=False,
            )
        except Exception:
            logger.debug("Provider error details for %s", ticker, exc_info=True)
            raise ProviderError(f"Failed to fetch data for {ticker}") from None

        if df.empty:
            raise TickerNotFoundError(ticker)

        # Normalize yfinance multi-level columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"adj close": "adj_close"})
        # Keep only required columns
        cols = [
            c
            for c in ["date", "open", "high", "low", "close", "volume"]
            if c in df.columns
        ]
        df = df[cols]
        df["date"] = pd.to_datetime(df["date"]).dt.date
        return df

    def validate_ticker(self, ticker: str) -> bool:
        try:
            info = yf.Ticker(ticker).info
            return bool(info.get("regularMarketPrice"))
        except Exception:
            return False

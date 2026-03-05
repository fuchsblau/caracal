"""Market data types and exceptions."""

import pandas as pd


class ProviderError(Exception):
    """Base exception for provider errors."""


class TickerNotFoundError(ProviderError):
    """Raised when a ticker symbol is not found."""

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(f"Ticker not found: {ticker}")


class StorageError(Exception):
    """Base exception for storage errors."""


OHLCV_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def assert_ohlcv_schema(df: pd.DataFrame) -> None:
    """Validate that a DataFrame conforms to the OHLCV schema.

    Used in tests to enforce provider output contract.
    """
    missing = set(OHLCV_COLUMNS) - set(df.columns)
    assert not missing, f"Missing columns: {missing}"

    dates = list(df["date"])
    assert dates == sorted(dates), "Dates not sorted ascending"

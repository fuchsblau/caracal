"""Market data types and exceptions."""

import re

import pandas as pd

_SECRET_PARAMS = re.compile(
    r"((?:api_?key|token|api_?token|secret)=)[^&]*", re.IGNORECASE
)


def sanitize_url(url: str) -> str:
    """Mask secret query parameters in a URL.

    Replaces the values of known secret parameters (apikey, api_key, token,
    api_token, secret) with '***' to prevent API key leakage in logs and
    error messages.
    """
    return _SECRET_PARAMS.sub(r"\1***", url)


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

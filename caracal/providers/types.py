"""Market data types and exceptions."""

import re

import pandas as pd

_SECRET_PARAMS = re.compile(
    r"((?:api_?key|token|api_?token|secret)=)[^&]*", re.IGNORECASE
)

_TICKER_PATTERN = re.compile(r"^[A-Z0-9.]{1,12}$")


def sanitize_url(url: str) -> str:
    """Mask secret query parameters in a URL.

    Replaces the values of known secret parameters (apikey, api_key, token,
    api_token, secret) with '***' to prevent API key leakage in logs and
    error messages.
    """
    return _SECRET_PARAMS.sub(r"\1***", url)


def validate_ticker_format(ticker: str) -> bool:
    """Validate ticker symbol format.

    Returns True if the ticker matches the expected format: 1-12 uppercase
    alphanumeric characters or dots (e.g. 'AAPL', 'BRK.B', 'SAP.DE').
    Returns False for empty strings, overly long inputs, or strings
    containing unexpected characters.
    """
    return bool(_TICKER_PATTERN.match(ticker))


class ProviderError(Exception):
    """Base exception for provider errors."""


class RateLimitError(ProviderError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, provider: str, retry_after: int | None = None) -> None:
        self.retry_after = retry_after
        msg = f"{provider} API rate limit exceeded"
        if retry_after:
            msg += f" (retry after {retry_after}s)"
        super().__init__(msg)


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

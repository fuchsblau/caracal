"""Market data types and exceptions."""


class ProviderError(Exception):
    """Base exception for provider errors."""


class TickerNotFoundError(ProviderError):
    """Raised when a ticker symbol is not found."""

    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(f"Ticker not found: {ticker}")


class StorageError(Exception):
    """Base exception for storage errors."""

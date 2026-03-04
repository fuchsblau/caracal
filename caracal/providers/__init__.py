"""Market data providers."""

from datetime import date
from typing import Protocol

import pandas as pd

from caracal.providers.yahoo import YahooProvider


class MarketDataProvider(Protocol):
    """Interface for market data providers."""

    @property
    def name(self) -> str: ...

    def fetch_ohlcv(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame: ...

    def validate_ticker(self, ticker: str) -> bool: ...


PROVIDERS: dict[str, type] = {
    "yahoo": YahooProvider,
}


def get_provider(name: str = "yahoo") -> MarketDataProvider:
    """Get a provider instance by name.

    Args:
        name: Provider name. Default: "yahoo".

    Returns:
        Provider instance.

    Raises:
        ValueError: If provider name is unknown.
    """
    cls = PROVIDERS.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown provider: {name}. Available: {', '.join(PROVIDERS)}"
        )
    return cls()

"""Market data providers."""

import importlib
from datetime import date
from typing import Protocol

import pandas as pd


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


_PROVIDER_MAP: dict[str, tuple[str, str]] = {
    "yahoo": ("caracal.providers.yahoo", "YahooProvider"),
    "massive": ("caracal.providers.massive", "MassiveProvider"),
    "ibkr": ("caracal.providers.ibkr", "IBKRProvider"),
}


def get_provider(name: str = "yahoo", **kwargs) -> MarketDataProvider:
    """Get a provider instance by name with lazy loading.

    Args:
        name: Provider name. Default: "yahoo".
        **kwargs: Provider-specific configuration.

    Returns:
        Provider instance.

    Raises:
        ValueError: If provider name is unknown.
        ImportError: If provider dependencies are not installed.
    """
    if name not in _PROVIDER_MAP:
        available = ", ".join(sorted(_PROVIDER_MAP))
        raise ValueError(
            f"Unknown provider: {name}. Available: {available}"
        )

    module_path, class_name = _PROVIDER_MAP[name]
    try:
        module = importlib.import_module(module_path)
    except ImportError:
        raise ImportError(
            f"Provider '{name}' requires extra dependencies. "
            f"Install with: pip install caracal-trading[{name}]"
        ) from None

    cls = getattr(module, class_name)
    return cls(**kwargs)

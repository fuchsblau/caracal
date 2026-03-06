"""Central normalization pipeline for market data providers."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

import pandas as pd

from caracal.providers.types import OHLCV_COLUMNS

if TYPE_CHECKING:
    from caracal.providers import MarketDataProvider


def normalize_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """Enforce OHLCV schema on any provider's output.

    Idempotent: running on already-normalized data is a no-op.
    """
    if df.empty:
        return df[OHLCV_COLUMNS] if all(c in df.columns for c in OHLCV_COLUMNS) else df

    # 1. Type enforcement
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)
    df["volume"] = df["volume"].astype(int)

    # 2. Date normalization (datetime -> date)
    # Note: datetime is a subclass of date, so we check for the exact type.
    if hasattr(df["date"].iloc[0], "hour") and type(df["date"].iloc[0]) is not date:
        df["date"] = df["date"].apply(
            lambda dt: dt.date() if isinstance(dt, datetime) else dt,
        )

    # 3. Ascending sort
    df = df.sort_values("date").reset_index(drop=True)

    # 4. Column selection (strip extras like adjusted_close)
    return df[OHLCV_COLUMNS]


class NormalizedProvider:
    """Decorator that wraps any MarketDataProvider with post-normalization."""

    def __init__(self, inner: MarketDataProvider) -> None:
        self._inner = inner

    @property
    def name(self) -> str:
        return self._inner.name

    def fetch_ohlcv(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        df = self._inner.fetch_ohlcv(ticker, start_date, end_date)
        return normalize_pipeline(df)

    def validate_ticker(self, ticker: str) -> bool:
        return self._inner.validate_ticker(ticker)

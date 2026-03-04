"""Storage layer."""

from datetime import date
from typing import Protocol

import pandas as pd


class StorageProtocol(Protocol):
    """Interface for data persistence."""

    def store_ohlcv(self, ticker: str, df: pd.DataFrame) -> int: ...

    def get_ohlcv(
        self, ticker: str, start_date: date | None = None, end_date: date | None = None
    ) -> pd.DataFrame: ...

    def get_latest_date(self, ticker: str) -> date | None: ...

    def store_indicators(self, ticker: str, df: pd.DataFrame) -> int: ...

    def get_indicators(
        self, ticker: str, names: list[str] | None = None
    ) -> pd.DataFrame: ...

"""Simple Moving Average indicator."""

import pandas as pd


class SMAIndicator:
    def __init__(self, period: int = 20) -> None:
        self._period = period

    @property
    def name(self) -> str:
        return f"sma_{self._period}"

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].rolling(window=self._period).mean()

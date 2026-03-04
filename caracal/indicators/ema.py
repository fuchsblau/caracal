"""Exponential Moving Average indicator."""

import pandas as pd


class EMAIndicator:
    def __init__(self, period: int = 12) -> None:
        self._period = period

    @property
    def name(self) -> str:
        return f"ema_{self._period}"

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].ewm(span=self._period, adjust=False).mean()

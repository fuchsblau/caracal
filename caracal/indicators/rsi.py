"""Relative Strength Index indicator."""

import pandas as pd


class RSIIndicator:
    def __init__(self, period: int = 14) -> None:
        self._period = period

    @property
    def name(self) -> str:
        return f"rsi_{self._period}"

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(com=self._period - 1, min_periods=self._period).mean()
        avg_loss = loss.ewm(com=self._period - 1, min_periods=self._period).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

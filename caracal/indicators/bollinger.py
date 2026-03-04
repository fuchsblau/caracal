"""Bollinger Bands indicator."""

import pandas as pd


class BollingerIndicator:
    def __init__(self, period: int = 20, std_dev: float = 2.0) -> None:
        self._period = period
        self._std_dev = std_dev

    @property
    def name(self) -> str:
        return "bollinger"

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        middle = df["close"].rolling(window=self._period).mean()
        std = df["close"].rolling(window=self._period).std()
        return pd.DataFrame(
            {
                "upper": middle + self._std_dev * std,
                "middle": middle,
                "lower": middle - self._std_dev * std,
            }
        )

"""Moving Average Convergence Divergence indicator."""

import pandas as pd


class MACDIndicator:
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9) -> None:
        self._fast = fast
        self._slow = slow
        self._signal = signal

    @property
    def name(self) -> str:
        return "macd"

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        ema_fast = df["close"].ewm(span=self._fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=self._slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self._signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return pd.DataFrame(
            {
                "macd": macd_line,
                "signal": signal_line,
                "histogram": histogram,
            }
        )

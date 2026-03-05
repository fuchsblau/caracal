"""Rule-based entry point calculation."""

from typing import Any

import pandas as pd

from caracal.indicators.bollinger import BollingerIndicator
from caracal.output.precision import PERCENT_DECIMALS
from caracal.indicators.ema import EMAIndicator
from caracal.indicators.macd import MACDIndicator
from caracal.indicators.rsi import RSIIndicator
from caracal.indicators.sma import SMAIndicator


def calculate_entry_signal(df: pd.DataFrame) -> dict[str, Any]:
    """Calculate entry signal based on technical indicators.

    Returns dict with keys: signal, confidence, indicators
    """
    if len(df) < 30:
        return {"signal": "hold", "confidence": 0.0, "indicators": {}}

    sma_20 = SMAIndicator(20).calculate(df)
    sma_50 = SMAIndicator(50).calculate(df)
    ema_12 = EMAIndicator(12).calculate(df)
    rsi = RSIIndicator(14).calculate(df)
    macd_df = MACDIndicator().calculate(df)
    bollinger = BollingerIndicator().calculate(df)

    latest_close = df["close"].iloc[-1]
    signals: list[float] = []  # positive = buy, negative = sell

    # Rule 1: Price above SMA 20 -> bullish
    if pd.notna(sma_20.iloc[-1]):
        signals.append(1.0 if latest_close > sma_20.iloc[-1] else -1.0)

    # Rule 2: SMA 20 > SMA 50 (golden cross tendency)
    if pd.notna(sma_50.iloc[-1]) and pd.notna(sma_20.iloc[-1]):
        signals.append(1.0 if sma_20.iloc[-1] > sma_50.iloc[-1] else -1.0)

    # Rule 3: RSI not overbought/oversold
    if pd.notna(rsi.iloc[-1]):
        rsi_val = rsi.iloc[-1]
        if rsi_val < 30:
            signals.append(1.5)  # oversold = buy opportunity
        elif rsi_val > 70:
            signals.append(-1.5)  # overbought = sell signal
        else:
            signals.append(0.0)

    # Rule 4: MACD histogram positive
    if pd.notna(macd_df["histogram"].iloc[-1]):
        signals.append(1.0 if macd_df["histogram"].iloc[-1] > 0 else -1.0)

    # Rule 5: Price near lower Bollinger band = buy opportunity
    if pd.notna(bollinger["lower"].iloc[-1]):
        band_width = bollinger["upper"].iloc[-1] - bollinger["lower"].iloc[-1]
        if band_width > 0:
            position = (latest_close - bollinger["lower"].iloc[-1]) / band_width
            signals.append(1.0 - position)  # closer to lower = more bullish

    if not signals:
        return {"signal": "hold", "confidence": 0.0, "indicators": {}}

    avg_signal = sum(signals) / len(signals)
    confidence = min(abs(avg_signal), 1.0)

    if avg_signal > 0.2:
        signal = "buy"
    elif avg_signal < -0.2:
        signal = "sell"
    else:
        signal = "hold"

    indicators = {
        "sma_20": _safe_val(sma_20.iloc[-1]),
        "sma_50": _safe_val(sma_50.iloc[-1]),
        "ema_12": _safe_val(ema_12.iloc[-1]),
        "rsi_14": _safe_val(rsi.iloc[-1]),
        "macd": _safe_val(macd_df["macd"].iloc[-1]),
        "macd_signal": _safe_val(macd_df["signal"].iloc[-1]),
        "bollinger_upper": _safe_val(bollinger["upper"].iloc[-1]),
        "bollinger_lower": _safe_val(bollinger["lower"].iloc[-1]),
    }

    return {
        "signal": signal,
        "confidence": round(confidence, PERCENT_DECIMALS),
        "indicators": indicators,
    }


def _safe_val(val: Any) -> float | None:
    """Convert NaN to None."""
    if pd.isna(val):
        return None
    return float(val)

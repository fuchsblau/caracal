"""Rule-based entry point calculation."""

from typing import Any

import pandas as pd

from caracal.indicators.bollinger import BollingerIndicator
from caracal.indicators.ema import EMAIndicator
from caracal.indicators.macd import MACDIndicator
from caracal.indicators.rsi import RSIIndicator
from caracal.indicators.sma import SMAIndicator
from caracal.output.precision import PERCENT_DECIMALS

_EMPTY_RESULT: dict[str, Any] = {"signal": "hold", "confidence": 0.0, "indicators": {}}


def calculate_entry_signal(
    df: pd.DataFrame, *, include_scores: bool = False
) -> dict[str, Any]:
    """Calculate entry signal based on technical indicators.

    Returns dict with keys: signal, confidence, indicators.
    If include_scores=True, also returns 'scores' (list[float] of individual rule scores).
    """
    if len(df) < 30:
        result = dict(_EMPTY_RESULT)
        if include_scores:
            result["scores"] = []
        return result

    sma_20 = SMAIndicator(20).calculate(df)
    sma_50 = SMAIndicator(50).calculate(df)
    ema_12 = EMAIndicator(12).calculate(df)
    rsi = RSIIndicator(14).calculate(df)
    macd_df = MACDIndicator().calculate(df)
    bollinger = BollingerIndicator().calculate(df)

    latest_close = df["close"].iloc[-1]
    signals = _collect_signals(latest_close, sma_20, sma_50, rsi, macd_df, bollinger)

    if not signals:
        result = dict(_EMPTY_RESULT)
        if include_scores:
            result["scores"] = []
        return result

    avg_signal = sum(signals) / len(signals)
    confidence = min(abs(avg_signal), 1.0)
    signal = _classify_signal(avg_signal)

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

    result = {
        "signal": signal,
        "confidence": round(confidence, PERCENT_DECIMALS),
        "indicators": indicators,
    }
    if include_scores:
        result["scores"] = signals
    return result


def _collect_signals(
    latest_close: float,
    sma_20: pd.Series,
    sma_50: pd.Series,
    rsi: pd.Series,
    macd_df: pd.DataFrame,
    bollinger: pd.DataFrame,
) -> list[float]:
    """Evaluate all rules and collect signal scores."""
    signals: list[float] = []

    _rule_price_vs_sma(signals, latest_close, sma_20)
    _rule_sma_crossover(signals, sma_20, sma_50)
    _rule_rsi(signals, rsi)
    _rule_macd(signals, macd_df)
    _rule_bollinger(signals, latest_close, bollinger)

    return signals


def _rule_price_vs_sma(
    signals: list[float], latest_close: float, sma_20: pd.Series
) -> None:
    """Price above SMA 20 is bullish."""
    if pd.notna(sma_20.iloc[-1]):
        signals.append(1.0 if latest_close > sma_20.iloc[-1] else -1.0)


def _rule_sma_crossover(
    signals: list[float], sma_20: pd.Series, sma_50: pd.Series
) -> None:
    """SMA 20 > SMA 50 indicates golden cross tendency."""
    if pd.notna(sma_50.iloc[-1]) and pd.notna(sma_20.iloc[-1]):
        signals.append(1.0 if sma_20.iloc[-1] > sma_50.iloc[-1] else -1.0)


def _rule_rsi(signals: list[float], rsi: pd.Series) -> None:
    """RSI below 30 is oversold (buy), above 70 is overbought (sell)."""
    if not pd.notna(rsi.iloc[-1]):
        return
    rsi_val = rsi.iloc[-1]
    if rsi_val < 30:
        signals.append(1.5)
    elif rsi_val > 70:
        signals.append(-1.5)
    else:
        signals.append(0.0)


def _rule_macd(signals: list[float], macd_df: pd.DataFrame) -> None:
    """Positive MACD histogram is bullish."""
    if pd.notna(macd_df["histogram"].iloc[-1]):
        signals.append(1.0 if macd_df["histogram"].iloc[-1] > 0 else -1.0)


def _rule_bollinger(
    signals: list[float], latest_close: float, bollinger: pd.DataFrame
) -> None:
    """Price near lower Bollinger band is a buy opportunity."""
    if not pd.notna(bollinger["lower"].iloc[-1]):
        return
    band_width = bollinger["upper"].iloc[-1] - bollinger["lower"].iloc[-1]
    if band_width > 0:
        position = (latest_close - bollinger["lower"].iloc[-1]) / band_width
        signals.append(1.0 - position)


def _classify_signal(avg_signal: float) -> str:
    if avg_signal > 0.2:
        return "buy"
    if avg_signal < -0.2:
        return "sell"
    return "hold"


def _safe_val(val: Any) -> float | None:
    """Convert NaN to None."""
    if pd.isna(val):
        return None
    return float(val)

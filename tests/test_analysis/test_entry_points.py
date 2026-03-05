from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from caracal.analysis.entry_points import (
    _classify_signal,
    _rule_bollinger,
    _rule_rsi,
    _safe_val,
    calculate_entry_signal,
)


@pytest.fixture
def bullish_data():
    """Data where indicators suggest a buy signal."""
    n = 60
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(n)]
    # Price trending up strongly
    closes = [100.0 + i * 0.5 for i in range(n)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1000000] * n,
        }
    )


@pytest.fixture
def bearish_data():
    """Data that rises then declines with mixed days (RSI stays in neutral zone).

    Rise for 40 days, then 20 days of gentle zigzag decline.
    This produces: price < SMA(20), MACD negative, RSI ~35 (neutral),
    SMA(20) > SMA(50) still (bullish crossover from prior rise).
    Net signal is in the hold zone (-0.2 to 0.2).
    """
    n = 60
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(n)]
    closes = [100.0 + i * 0.3 for i in range(40)]
    for i in range(20):
        closes.append(closes[-1] + (-0.15))
    return pd.DataFrame(
        {
            "date": dates,
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1000000] * n,
        }
    )


# -- Integration tests: full pipeline --


def test_returns_signal_and_confidence(bullish_data):
    result = calculate_entry_signal(bullish_data)
    assert "signal" in result
    assert "confidence" in result
    assert result["signal"] in ("buy", "sell", "hold")
    assert 0.0 <= result["confidence"] <= 1.0


def test_includes_indicator_values(bullish_data):
    result = calculate_entry_signal(bullish_data)
    assert "indicators" in result


def test_insufficient_data():
    df = pd.DataFrame(
        {
            "date": [date(2024, 1, 1)],
            "open": [100.0],
            "high": [105.0],
            "low": [99.0],
            "close": [104.0],
            "volume": [1000000],
        }
    )
    result = calculate_entry_signal(df)
    assert result["signal"] == "hold"
    assert result["confidence"] == 0.0


def test_confidence_rounded_to_two_decimals(bullish_data):
    """Confidence should be rounded to 2 decimal places."""
    result = calculate_entry_signal(bullish_data)
    confidence_str = str(result["confidence"])
    if "." in confidence_str:
        decimals = len(confidence_str.split(".")[1])
        assert decimals <= 2, (
            f"Confidence has {decimals} decimals: {result['confidence']}"
        )


def test_bullish_data_produces_buy(bullish_data):
    """Strong uptrend should produce a buy signal."""
    result = calculate_entry_signal(bullish_data)
    assert result["signal"] == "buy"


def test_bearish_data_not_buy(bearish_data):
    """Rise-then-decline data should not be bullish."""
    result = calculate_entry_signal(bearish_data)
    assert result["signal"] != "buy"


def test_indicator_values_are_floats_or_none(bullish_data):
    """Every indicator value should be float or None (NaN -> None)."""
    result = calculate_entry_signal(bullish_data)
    for key, val in result["indicators"].items():
        assert val is None or isinstance(val, float), f"{key}: {val}"


def test_exactly_30_data_points():
    """Exactly 30 rows should be enough to calculate (boundary)."""
    n = 30
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(n)]
    closes = [100.0 + i * 0.5 for i in range(n)]
    df = pd.DataFrame(
        {
            "date": dates,
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1000000] * n,
        }
    )
    result = calculate_entry_signal(df)
    assert result["signal"] in ("buy", "sell", "hold")


def test_29_data_points_returns_empty():
    """29 rows should be insufficient (< 30 threshold)."""
    n = 29
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(n)]
    closes = [100.0 + i for i in range(n)]
    df = pd.DataFrame(
        {
            "date": dates,
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1000000] * n,
        }
    )
    result = calculate_entry_signal(df)
    assert result == {"signal": "hold", "confidence": 0.0, "indicators": {}}


def test_constant_prices_all_signals_bearish():
    """Constant prices: SMA=price (not >), MACD=0 (not >0), Bollinger width=0.

    All > comparisons evaluate False, producing -1.0 signals.
    RSI is NaN (0/0), Bollinger skipped (band_width=0).
    """
    n = 60
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(n)]
    df = pd.DataFrame(
        {
            "date": dates,
            "open": [100.0] * n,
            "high": [100.5] * n,
            "low": [99.5] * n,
            "close": [100.0] * n,
            "volume": [1000000] * n,
        }
    )
    result = calculate_entry_signal(df)
    assert result["signal"] == "sell"
    assert result["confidence"] == 1.0


# -- Unit tests: internal functions for branch coverage --


class TestClassifySignal:
    def test_buy(self):
        assert _classify_signal(0.5) == "buy"

    def test_sell(self):
        assert _classify_signal(-0.5) == "sell"

    def test_hold_zero(self):
        assert _classify_signal(0.0) == "hold"

    def test_hold_positive_boundary(self):
        assert _classify_signal(0.2) == "hold"

    def test_hold_negative_boundary(self):
        assert _classify_signal(-0.2) == "hold"

    def test_buy_just_above_threshold(self):
        assert _classify_signal(0.21) == "buy"

    def test_sell_just_below_threshold(self):
        assert _classify_signal(-0.21) == "sell"


class TestSafeVal:
    def test_nan_returns_none(self):
        assert _safe_val(float("nan")) is None

    def test_numpy_nan_returns_none(self):
        assert _safe_val(np.nan) is None

    def test_float_returns_float(self):
        assert _safe_val(42.5) == 42.5

    def test_int_returns_float(self):
        result = _safe_val(42)
        assert result == 42.0
        assert isinstance(result, float)


class TestRuleRsi:
    def test_oversold_below_30(self):
        signals: list[float] = []
        rsi = pd.Series([25.0])
        _rule_rsi(signals, rsi)
        assert signals == [1.5]

    def test_overbought_above_70(self):
        signals: list[float] = []
        rsi = pd.Series([75.0])
        _rule_rsi(signals, rsi)
        assert signals == [-1.5]

    def test_neutral_between_30_and_70(self):
        signals: list[float] = []
        rsi = pd.Series([50.0])
        _rule_rsi(signals, rsi)
        assert signals == [0.0]

    def test_nan_skips(self):
        signals: list[float] = []
        rsi = pd.Series([float("nan")])
        _rule_rsi(signals, rsi)
        assert signals == []


class TestRuleBollinger:
    def test_nan_lower_skips(self):
        signals: list[float] = []
        bollinger = pd.DataFrame(
            {"lower": [float("nan")], "upper": [float("nan")]}
        )
        _rule_bollinger(signals, 100.0, bollinger)
        assert signals == []

    def test_zero_bandwidth_skips(self):
        signals: list[float] = []
        bollinger = pd.DataFrame({"lower": [100.0], "upper": [100.0]})
        _rule_bollinger(signals, 100.0, bollinger)
        assert signals == []

    def test_price_at_lower_band(self):
        signals: list[float] = []
        bollinger = pd.DataFrame({"lower": [90.0], "upper": [110.0]})
        _rule_bollinger(signals, 90.0, bollinger)
        assert signals == [pytest.approx(1.0)]

    def test_price_at_upper_band(self):
        signals: list[float] = []
        bollinger = pd.DataFrame({"lower": [90.0], "upper": [110.0]})
        _rule_bollinger(signals, 110.0, bollinger)
        # position = (110-90)/20 = 1.0, signal = 1.0 - 1.0 = 0.0
        assert signals == [pytest.approx(0.0)]

    def test_price_above_upper_band(self):
        signals: list[float] = []
        bollinger = pd.DataFrame({"lower": [90.0], "upper": [110.0]})
        _rule_bollinger(signals, 120.0, bollinger)
        # position = (120-90)/20 = 1.5, signal = 1.0 - 1.5 = -0.5
        assert signals == [pytest.approx(-0.5)]

    def test_price_at_middle(self):
        signals: list[float] = []
        bollinger = pd.DataFrame({"lower": [90.0], "upper": [110.0]})
        _rule_bollinger(signals, 100.0, bollinger)
        assert signals == [pytest.approx(0.5)]

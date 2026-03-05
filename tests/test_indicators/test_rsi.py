import pandas as pd
import pytest

from caracal.indicators.rsi import RSIIndicator


def test_rsi_name():
    assert RSIIndicator(period=14).name == "rsi_14"


def test_rsi_range(sample_ohlcv):
    ind = RSIIndicator(period=14)
    result = ind.calculate(sample_ohlcv)
    valid = result.dropna()
    assert all(0 <= v <= 100 for v in valid)


def test_rsi_all_up():
    """Monotonically increasing prices should give RSI near 100."""
    df = pd.DataFrame({"close": [float(i) for i in range(1, 30)]})
    ind = RSIIndicator(period=14)
    result = ind.calculate(df)
    assert result.iloc[-1] == pytest.approx(100.0)


def test_rsi_all_down():
    """Monotonically decreasing prices should give RSI near 0."""
    df = pd.DataFrame({"close": [float(100 - i) for i in range(30)]})
    ind = RSIIndicator(period=14)
    result = ind.calculate(df)
    assert result.iloc[-1] == pytest.approx(0.0)


def test_rsi_constant_prices():
    """Constant prices -> no gain, no loss -> RSI should handle gracefully."""
    df = pd.DataFrame({"close": [50.0] * 30})
    ind = RSIIndicator(period=14)
    result = ind.calculate(df)
    # No movement = neutral (pandas returns NaN for 0/0)
    # Test that it doesn't crash and returns something in [0, 100] or NaN
    last = result.iloc[-1]
    assert pd.isna(last) or (0 <= last <= 100)


def test_rsi_boundary_period_exact():
    """With exactly period+1 data points, RSI should be calculable."""
    df = pd.DataFrame({"close": [float(100 + i) for i in range(15)]})
    ind = RSIIndicator(period=14)
    result = ind.calculate(df)
    assert result.notna().sum() >= 1

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

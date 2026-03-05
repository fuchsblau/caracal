import pandas as pd
import pytest

from caracal.indicators.macd import MACDIndicator


def test_macd_name():
    assert MACDIndicator().name == "macd"


def test_macd_returns_three_series(sample_ohlcv):
    ind = MACDIndicator()
    result = ind.calculate(sample_ohlcv)
    assert isinstance(result, pd.DataFrame)
    assert "macd" in result.columns
    assert "signal" in result.columns
    assert "histogram" in result.columns


def test_macd_histogram_equals_macd_minus_signal(sample_ohlcv):
    """Histogram = MACD line - Signal line (by definition)."""
    result = MACDIndicator().calculate(sample_ohlcv)
    for i in range(len(result)):
        expected = result["macd"].iloc[i] - result["signal"].iloc[i]
        assert result["histogram"].iloc[i] == pytest.approx(expected)


def test_macd_constant_prices_all_zero():
    """Constant prices -> EMA_fast = EMA_slow -> MACD = 0."""
    df = pd.DataFrame({"close": [100.0] * 50})
    result = MACDIndicator().calculate(df)
    assert result["macd"].iloc[-1] == pytest.approx(0.0)
    assert result["signal"].iloc[-1] == pytest.approx(0.0)
    assert result["histogram"].iloc[-1] == pytest.approx(0.0)


def test_macd_uptrend_positive():
    """Strong uptrend -> fast EMA > slow EMA -> positive MACD."""
    df = pd.DataFrame({"close": [float(i) for i in range(60)]})
    result = MACDIndicator().calculate(df)
    assert result["macd"].iloc[-1] > 0

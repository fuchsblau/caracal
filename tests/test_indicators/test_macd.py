import pandas as pd

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

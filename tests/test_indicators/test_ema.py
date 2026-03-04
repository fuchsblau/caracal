import pandas as pd

from caracal.indicators.ema import EMAIndicator


def test_ema_name():
    assert EMAIndicator(period=12).name == "ema_12"


def test_ema_calculation(sample_ohlcv):
    ind = EMAIndicator(period=3)
    result = ind.calculate(sample_ohlcv)
    assert isinstance(result, pd.Series)
    assert len(result) == 20
    assert result.notna().sum() > 0

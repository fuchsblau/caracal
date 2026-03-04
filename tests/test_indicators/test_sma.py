import pandas as pd
import pytest

from caracal.indicators.sma import SMAIndicator


def test_sma_name():
    ind = SMAIndicator(period=20)
    assert ind.name == "sma_20"


def test_sma_calculation(sample_ohlcv):
    ind = SMAIndicator(period=3)
    result = ind.calculate(sample_ohlcv)
    assert isinstance(result, pd.Series)
    assert pd.isna(result.iloc[0])  # not enough data
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == pytest.approx(101.0)  # (100+101+102)/3
    assert result.iloc[3] == pytest.approx(102.0)  # (101+102+103)/3


def test_sma_full_period(sample_ohlcv):
    ind = SMAIndicator(period=20)
    result = ind.calculate(sample_ohlcv)
    assert pd.isna(result.iloc[18])
    assert result.iloc[19] == pytest.approx(109.5)  # avg(100..119)

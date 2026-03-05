import pandas as pd
import pytest

from caracal.indicators.ema import EMAIndicator


def test_ema_name():
    assert EMAIndicator(period=12).name == "ema_12"


def test_ema_calculation(sample_ohlcv):
    ind = EMAIndicator(period=3)
    result = ind.calculate(sample_ohlcv)
    assert isinstance(result, pd.Series)
    assert len(result) == 20
    assert result.notna().sum() > 0


def test_ema_known_values(sample_ohlcv):
    """EMA with period=3 should match hand-calculated values.

    Closes: 100, 101, 102, 103, ...
    EMA(3) multiplier = 2/(3+1) = 0.5
    EMA[0] = 100
    EMA[1] = 101 * 0.5 + 100 * 0.5 = 100.5
    EMA[2] = 102 * 0.5 + 100.5 * 0.5 = 101.25
    EMA[3] = 103 * 0.5 + 101.25 * 0.5 = 102.125
    """
    ind = EMAIndicator(period=3)
    result = ind.calculate(sample_ohlcv)
    assert result.iloc[0] == pytest.approx(100.0)
    assert result.iloc[1] == pytest.approx(100.5)
    assert result.iloc[2] == pytest.approx(101.25)
    assert result.iloc[3] == pytest.approx(102.125)


def test_ema_all_same_prices():
    """EMA of constant prices should equal that price."""
    df = pd.DataFrame({"close": [50.0] * 20})
    result = EMAIndicator(period=5).calculate(df)
    for val in result:
        assert val == pytest.approx(50.0)

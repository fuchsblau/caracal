import pandas as pd
import pytest

from caracal.indicators.bollinger import BollingerIndicator


def test_bollinger_name():
    assert BollingerIndicator().name == "bollinger"


def test_bollinger_bands(sample_ohlcv):
    ind = BollingerIndicator(period=5, std_dev=2)
    result = ind.calculate(sample_ohlcv)
    assert isinstance(result, pd.DataFrame)
    assert "upper" in result.columns
    assert "middle" in result.columns
    assert "lower" in result.columns
    valid = result.dropna()
    assert all(valid["upper"] >= valid["middle"])
    assert all(valid["middle"] >= valid["lower"])


def test_bollinger_known_values():
    """Bollinger middle band = SMA, width = 2 * std_dev * rolling_std.

    5 constant prices -> std=0 -> all bands collapse to the price.
    """
    df = pd.DataFrame({"close": [100.0] * 10})
    result = BollingerIndicator(period=5, std_dev=2).calculate(df)
    valid = result.dropna()
    for _, row in valid.iterrows():
        assert row["upper"] == pytest.approx(100.0)
        assert row["middle"] == pytest.approx(100.0)
        assert row["lower"] == pytest.approx(100.0)


def test_bollinger_band_width_scales_with_std_dev():
    """Doubling std_dev parameter should double band width."""
    df = pd.DataFrame({"close": [100.0, 102.0, 98.0, 101.0, 99.0] * 4})
    narrow = BollingerIndicator(period=5, std_dev=1).calculate(df)
    wide = BollingerIndicator(period=5, std_dev=2).calculate(df)
    valid_idx = narrow.dropna().index
    for i in valid_idx:
        narrow_width = narrow.loc[i, "upper"] - narrow.loc[i, "lower"]
        wide_width = wide.loc[i, "upper"] - wide.loc[i, "lower"]
        assert wide_width == pytest.approx(2 * narrow_width)

import pandas as pd

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

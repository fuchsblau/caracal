from datetime import date, timedelta

import pandas as pd
import pytest

from caracal.analysis.entry_points import calculate_entry_signal


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
    # Should have at most 2 decimal places
    if "." in confidence_str:
        decimals = len(confidence_str.split(".")[1])
        assert decimals <= 2, f"Confidence has {decimals} decimals: {result['confidence']}"

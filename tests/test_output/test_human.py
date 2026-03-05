from datetime import date

import pandas as pd

from caracal.output.human import _color_value, format_error_message, format_ohlcv_table


def test_format_ohlcv_table():
    df = pd.DataFrame(
        {
            "date": [date(2024, 1, 1)],
            "open": [100.0],
            "high": [105.0],
            "low": [99.0],
            "close": [104.0],
            "volume": [1000],
        }
    )
    output = format_ohlcv_table(df, "AAPL")
    assert "AAPL" in output
    assert "100" in output


def test_format_ohlcv_table_price_precision():
    """Prices should show exactly 2 decimal places."""
    df = pd.DataFrame(
        {
            "date": [date(2024, 1, 1)],
            "open": [100.123456],
            "high": [105.999999],
            "low": [99.1],
            "close": [104.50],
            "volume": [1000],
        }
    )
    output = format_ohlcv_table(df, "TEST")
    assert "100.12" in output
    assert "106.00" in output
    assert "99.10" in output
    assert "104.50" in output
    # Volume should be integer (no decimals)
    assert "1000" in output
    # Should NOT contain unformatted floats
    assert "100.123456" not in output


def test_format_error_message():
    output = format_error_message("Ticker not found: XYZ")
    assert "XYZ" in output


def test_color_value_uses_two_decimals():
    """Indicator values should show 2 decimal places, not 4."""
    result = _color_value("sma_20", 178.3456)
    assert result.plain == "178.35"


def test_color_value_rsi_two_decimals():
    result = _color_value("rsi_14", 38.2199)
    assert result.plain == "38.22"

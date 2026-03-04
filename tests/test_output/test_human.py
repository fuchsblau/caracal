from datetime import date

import pandas as pd

from caracal.output.human import format_error_message, format_ohlcv_table


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


def test_format_error_message():
    output = format_error_message("Ticker not found: XYZ")
    assert "XYZ" in output

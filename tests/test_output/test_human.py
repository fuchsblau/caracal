from datetime import date

import pandas as pd

from caracal.output.human import (
    _color_value,
    format_entry_signal,
    format_error_message,
    format_fetch_success,
    format_header,
    format_indicators_dict,
    format_logo,
    format_ohlcv_table,
    format_success_message,
    format_warning,
    format_watchlist_items,
    format_watchlist_list,
    format_watchlist_prices,
)


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


def test_format_entry_signal_confidence_precision():
    """Confidence should show 2 decimal places as percent."""
    result_data = {
        "signal": "buy",
        "confidence": 0.7234,
        "indicators": {},
    }
    output = format_entry_signal(result_data, "AAPL")
    assert "72.34%" in output


def test_format_entry_signal_with_indicators():
    """Entry signal with indicator values should show indicator table."""
    result_data = {
        "signal": "sell",
        "confidence": 0.65,
        "indicators": {
            "sma_20": 178.35,
            "rsi_14": 75.0,
            "macd": None,
        },
    }
    output = format_entry_signal(result_data, "AAPL")
    assert "SELL" in output
    assert "sma_20" in output
    assert "178.35" in output
    assert "N/A" in output  # macd is None


def test_format_watchlist_prices_precision():
    """Watchlist prices should use precision constants."""
    prices = [
        {"ticker": "AAPL", "close": 178.123, "change": 1.567, "change_pct": 0.889},
    ]
    output = format_watchlist_prices(prices, "test")
    assert "178.12" in output
    assert "+1.57" in output
    assert "+0.89%" in output


def test_format_indicators_dict_with_values():
    indicators = {"sma_20": 178.35, "rsi_14": 65.42}
    output = format_indicators_dict(indicators, "AAPL")
    assert "sma_20" in output
    assert "178.35" in output
    assert "AAPL" in output


def test_format_indicators_dict_with_none():
    indicators = {"sma_50": None, "rsi_14": 45.0}
    output = format_indicators_dict(indicators, "TEST")
    assert "N/A" in output


def test_format_fetch_success_rows_added():
    output = format_fetch_success(42, "AAPL")
    assert "42" in output
    assert "AAPL" in output


def test_format_fetch_success_up_to_date():
    output = format_fetch_success(0, "AAPL")
    assert "up to date" in output.lower()


def test_format_success_message_simple():
    output = format_success_message("Config created")
    assert "Config created" in output


def test_format_success_message_with_details():
    output = format_success_message("Done", {"path": "/tmp/test.toml"})
    # Rich adds ANSI styling to paths; check parts separately
    assert "path" in output
    assert "test.toml" in output


def test_format_warning():
    output = format_warning("API rate limited")
    assert "API rate limited" in output


def test_format_header():
    output = format_header("Analysis Results")
    assert "Analysis Results" in output


def test_format_watchlist_list_table():
    watchlists = [
        {"name": "tech", "ticker_count": 5, "created_at": "2024-01-01"},
    ]
    output = format_watchlist_list(watchlists)
    assert "tech" in output
    assert "5" in output


def test_format_watchlist_items_table():
    output = format_watchlist_items(["AAPL", "GOOG"], "tech")
    assert "AAPL" in output
    assert "GOOG" in output
    assert "tech" in output


def test_format_logo():
    """Logo is ASCII block art, not literal text."""
    output = format_logo()
    # Logo uses Unicode block characters (e.g. ░█▀▀)
    assert len(output) > 0
    assert "\n" in output

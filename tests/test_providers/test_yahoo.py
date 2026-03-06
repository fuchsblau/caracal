import logging
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from caracal.providers.types import ProviderError, TickerNotFoundError
from caracal.providers.yahoo import YahooProvider


class TestYahooProvider:
    def test_name(self):
        provider = YahooProvider()
        assert provider.name == "yahoo"

    @patch("caracal.providers.yahoo.yf.download")
    def test_fetch_ohlcv_success(self, mock_download):
        mock_download.return_value = pd.DataFrame(
            {
                ("Open", "AAPL"): [100.0],
                ("High", "AAPL"): [105.0],
                ("Low", "AAPL"): [99.0],
                ("Close", "AAPL"): [104.0],
                ("Volume", "AAPL"): [1000000],
            },
            index=pd.DatetimeIndex([pd.Timestamp("2024-01-02")], name="Date"),
        )

        provider = YahooProvider()
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 3))

        assert len(result) == 1
        assert "close" in result.columns
        assert "date" in result.columns

    @patch("caracal.providers.yahoo.yf.download")
    def test_fetch_ohlcv_empty_raises(self, mock_download):
        mock_download.return_value = pd.DataFrame()

        provider = YahooProvider()
        with pytest.raises(TickerNotFoundError):
            provider.fetch_ohlcv("INVALID", date(2024, 1, 1), date(2024, 1, 3))

    @patch("caracal.providers.yahoo.yf.download")
    def test_fetch_ohlcv_api_error(self, mock_download):
        mock_download.side_effect = Exception("Network error")

        provider = YahooProvider()
        with pytest.raises(ProviderError, match="Failed to fetch data for AAPL"):
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 3))

    @patch("caracal.providers.yahoo.yf.download")
    def test_fetch_ohlcv_error_does_not_leak_details(self, mock_download):
        mock_download.side_effect = ConnectionError(
            "Connection to internal-proxy.corp:8080 refused"
        )

        provider = YahooProvider()
        with pytest.raises(ProviderError) as exc_info:
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))
        assert "internal-proxy" not in str(exc_info.value)
        assert "8080" not in str(exc_info.value)

    @patch("caracal.providers.yahoo.yf.download")
    def test_fetch_ohlcv_error_no_traceback_in_message(self, mock_download):
        """ProviderError message must not contain raw traceback text."""
        mock_download.side_effect = RuntimeError(
            "Traceback (most recent call last):\n  File yfinance/base.py"
        )
        provider = YahooProvider()
        with pytest.raises(ProviderError) as exc_info:
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))
        msg = str(exc_info.value)
        assert "Traceback" not in msg
        assert "yfinance" not in msg

    @patch("caracal.providers.yahoo.yf.download")
    def test_fetch_ohlcv_error_logs_debug_details(self, mock_download, caplog):
        """Original exception details should be logged at DEBUG level."""
        mock_download.side_effect = ValueError("some internal yfinance error")
        provider = YahooProvider()
        with caplog.at_level(logging.DEBUG, logger="caracal"):
            with pytest.raises(ProviderError):
                provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))
        assert any("AAPL" in r.message for r in caplog.records)

    @patch("caracal.providers.yahoo.yf.Ticker")
    def test_validate_ticker_valid(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 150.0}
        mock_ticker_cls.return_value = mock_ticker

        provider = YahooProvider()
        assert provider.validate_ticker("AAPL") is True

    @patch("caracal.providers.yahoo.yf.Ticker")
    def test_validate_ticker_invalid(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        mock_ticker_cls.return_value = mock_ticker

        provider = YahooProvider()
        assert provider.validate_ticker("INVALID") is False

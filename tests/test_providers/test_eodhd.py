"""Tests for EODHD market data provider."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests

from caracal.providers.types import (
    ProviderError,
    TickerNotFoundError,
    assert_ohlcv_schema,
)

_SAMPLE_JSON = [
    {
        "date": "2024-01-02",
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "close": 103.0,
        "adjusted_close": 104.0,
        "volume": 1000000,
    },
    {
        "date": "2024-01-03",
        "open": 101.0,
        "high": 106.0,
        "low": 100.0,
        "close": 104.0,
        "adjusted_close": 105.0,
        "volume": 1100000,
    },
]


class TestEODHDProvider:
    def test_name(self):
        from caracal.providers.eodhd import EODHDProvider

        provider = EODHDProvider(api_key="test_key")
        assert provider.name == "eodhd"

    def test_missing_api_key_raises(self):
        from caracal.providers.eodhd import EODHDProvider

        with pytest.raises(ProviderError, match="API key"):
            EODHDProvider()

    @patch("caracal.providers.eodhd.requests.get")
    def test_fetch_ohlcv_success(self, mock_get):
        from caracal.providers.eodhd import EODHDProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = _SAMPLE_JSON
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = EODHDProvider(api_key="test_key")
        df = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))
        assert len(df) == 2
        assert_ohlcv_schema(df)
        assert df.iloc[0]["close"] == 104.0  # adjusted_close mapped to close

    @patch("caracal.providers.eodhd.requests.get")
    def test_ticker_without_suffix_gets_default_exchange(self, mock_get):
        from caracal.providers.eodhd import EODHDProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = _SAMPLE_JSON
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = EODHDProvider(api_key="test_key", default_exchange="US")
        provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))
        call_url = mock_get.call_args[0][0]
        assert "AAPL.US" in call_url

    @patch("caracal.providers.eodhd.requests.get")
    def test_ticker_with_suffix_preserved(self, mock_get):
        from caracal.providers.eodhd import EODHDProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = _SAMPLE_JSON
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = EODHDProvider(api_key="test_key")
        provider.fetch_ohlcv("SAP.XETRA", date(2024, 1, 1), date(2024, 1, 5))
        call_url = mock_get.call_args[0][0]
        assert "SAP.XETRA" in call_url

    @patch("caracal.providers.eodhd.requests.get")
    def test_custom_default_exchange(self, mock_get):
        from caracal.providers.eodhd import EODHDProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = _SAMPLE_JSON
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = EODHDProvider(api_key="test_key", default_exchange="XETRA")
        provider.fetch_ohlcv("SAP", date(2024, 1, 1), date(2024, 1, 5))
        call_url = mock_get.call_args[0][0]
        assert "SAP.XETRA" in call_url

    @patch("caracal.providers.eodhd.requests.get")
    def test_fetch_ohlcv_empty_raises(self, mock_get):
        from caracal.providers.eodhd import EODHDProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = EODHDProvider(api_key="test_key")
        with pytest.raises(TickerNotFoundError):
            provider.fetch_ohlcv("INVALID", date(2024, 1, 1), date(2024, 1, 5))

    @patch("caracal.providers.eodhd.requests.get")
    def test_fetch_ohlcv_error_dict_response(self, mock_get):
        from caracal.providers.eodhd import EODHDProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"error": "Invalid API key"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = EODHDProvider(api_key="bad_key")
        with pytest.raises(TickerNotFoundError):
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))

    @patch("caracal.providers.eodhd.requests.get")
    def test_validate_ticker_valid(self, mock_get):
        from caracal.providers.eodhd import EODHDProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = _SAMPLE_JSON
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = EODHDProvider(api_key="test_key")
        assert provider.validate_ticker("AAPL") is True

    @patch("caracal.providers.eodhd.requests.get")
    def test_validate_ticker_invalid(self, mock_get):
        from caracal.providers.eodhd import EODHDProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = EODHDProvider(api_key="test_key")
        assert provider.validate_ticker("INVALID") is False

    @patch("caracal.providers.eodhd.requests.get")
    def test_fetch_ohlcv_http_error_raises_provider_error(self, mock_get):
        from caracal.providers.eodhd import EODHDProvider

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "429 Client Error: Too Many Requests for url: "
            "https://eodhd.com/api/eod/AAPL.US?api_token=SECRET_KEY"
        )
        mock_resp.status_code = 429
        mock_get.return_value = mock_resp

        provider = EODHDProvider(api_key="SECRET_KEY")
        with pytest.raises(ProviderError, match="rate limit"):
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))

    @patch("caracal.providers.eodhd.requests.get")
    def test_fetch_ohlcv_timeout_raises_provider_error(self, mock_get):
        from caracal.providers.eodhd import EODHDProvider

        mock_get.side_effect = requests.exceptions.Timeout(
            "Connection to eodhd.com timed out. "
            "(connect timeout=30)"
        )

        provider = EODHDProvider(api_key="SECRET_KEY")
        with pytest.raises(ProviderError, match="[Nn]etwork"):
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))

    @patch("caracal.providers.eodhd.requests.get")
    def test_fetch_ohlcv_connection_error_raises_provider_error(self, mock_get):
        from caracal.providers.eodhd import EODHDProvider

        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Failed to establish a new connection"
        )

        provider = EODHDProvider(api_key="SECRET_KEY")
        with pytest.raises(ProviderError, match="[Nn]etwork"):
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))

    @patch("caracal.providers.eodhd.requests.get")
    def test_fetch_ohlcv_error_does_not_leak_url(self, mock_get):
        from caracal.providers.eodhd import EODHDProvider

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error for url: "
            "https://eodhd.com/api/eod/AAPL.US?api_token=SECRET_KEY"
        )
        mock_resp.status_code = 500
        mock_get.return_value = mock_resp

        provider = EODHDProvider(api_key="SECRET_KEY")
        with pytest.raises(ProviderError) as exc_info:
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))

        error_msg = str(exc_info.value)
        assert "SECRET_KEY" not in error_msg
        assert "eodhd.com" not in error_msg

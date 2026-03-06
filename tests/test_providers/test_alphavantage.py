"""Tests for Alpha Vantage market data provider."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests

from caracal.providers.types import (
    ProviderError,
    TickerNotFoundError,
    assert_ohlcv_schema,
)

_SAMPLE_CSV = (
    "timestamp,open,high,low,close,adjusted_close,volume,"
    "dividend_amount,split_coefficient\n"
    "2024-01-03,101.0,106.0,100.0,105.0,105.5,1100000,0.0,1.0\n"
    "2024-01-02,100.0,105.0,99.0,104.0,104.5,1000000,0.0,1.0\n"
)


class TestAlphaVantageProvider:
    def test_name(self):
        from caracal.providers.alphavantage import AlphaVantageProvider

        provider = AlphaVantageProvider(api_key="test_key")
        assert provider.name == "alphavantage"

    def test_missing_api_key_raises(self):
        from caracal.providers.alphavantage import AlphaVantageProvider

        with pytest.raises(ProviderError, match="API key"):
            AlphaVantageProvider()

    @patch("caracal.providers.alphavantage.requests.get")
    def test_fetch_ohlcv_success(self, mock_get):
        from caracal.providers.alphavantage import AlphaVantageProvider

        mock_resp = MagicMock()
        mock_resp.text = _SAMPLE_CSV
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = AlphaVantageProvider(api_key="test_key")
        df = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))

        assert len(df) == 2
        assert_ohlcv_schema(df)
        assert df.iloc[0]["close"] == 104.5  # adjusted_close mapped to close
        assert df.iloc[1]["close"] == 105.5

    @patch("caracal.providers.alphavantage.requests.get")
    def test_fetch_ohlcv_date_filter(self, mock_get):
        from caracal.providers.alphavantage import AlphaVantageProvider

        mock_resp = MagicMock()
        mock_resp.text = _SAMPLE_CSV
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = AlphaVantageProvider(api_key="test_key")
        df = provider.fetch_ohlcv("AAPL", date(2024, 1, 2), date(2024, 1, 2))
        assert len(df) == 1
        assert df.iloc[0]["date"] == date(2024, 1, 2)

    @patch("caracal.providers.alphavantage.requests.get")
    def test_fetch_ohlcv_empty_raises(self, mock_get):
        from caracal.providers.alphavantage import AlphaVantageProvider

        mock_resp = MagicMock()
        mock_resp.text = (
            "timestamp,open,high,low,close,adjusted_close,volume,"
            "dividend_amount,split_coefficient\n"
        )
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = AlphaVantageProvider(api_key="test_key")
        with pytest.raises(TickerNotFoundError):
            provider.fetch_ohlcv("INVALID", date(2024, 1, 1), date(2024, 1, 5))

    @patch("caracal.providers.alphavantage.requests.get")
    def test_fetch_ohlcv_rate_limit_error(self, mock_get):
        from caracal.providers.alphavantage import AlphaVantageProvider

        mock_resp = MagicMock()
        mock_resp.text = '{"Note": "Thank you for using Alpha Vantage! Our standard API rate limit is 25 requests per day."}'
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = AlphaVantageProvider(api_key="test_key")
        with pytest.raises(ProviderError, match="Alpha Vantage API error"):
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))

    @patch("caracal.providers.alphavantage.requests.get")
    def test_fetch_passes_correct_params(self, mock_get):
        from caracal.providers.alphavantage import AlphaVantageProvider

        mock_resp = MagicMock()
        mock_resp.text = _SAMPLE_CSV
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = AlphaVantageProvider(api_key="my_key")
        provider.fetch_ohlcv("MSFT", date(2024, 1, 1), date(2024, 1, 5))

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["symbol"] == "MSFT"
        assert params["apikey"] == "my_key"
        assert params["datatype"] == "csv"
        assert params["function"] == "TIME_SERIES_DAILY_ADJUSTED"

    @patch("caracal.providers.alphavantage.requests.get")
    def test_validate_ticker_valid(self, mock_get):
        from caracal.providers.alphavantage import AlphaVantageProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "bestMatches": [{"1. symbol": "AAPL", "2. name": "Apple Inc"}]
        }
        mock_get.return_value = mock_resp

        provider = AlphaVantageProvider(api_key="test_key")
        assert provider.validate_ticker("AAPL") is True

    @patch("caracal.providers.alphavantage.requests.get")
    def test_validate_ticker_invalid(self, mock_get):
        from caracal.providers.alphavantage import AlphaVantageProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"bestMatches": []}
        mock_get.return_value = mock_resp

        provider = AlphaVantageProvider(api_key="test_key")
        assert provider.validate_ticker("ZZZZZZZ") is False

    @patch("caracal.providers.alphavantage.requests.get")
    def test_fetch_ohlcv_http_error_raises_provider_error(self, mock_get):
        from caracal.providers.alphavantage import AlphaVantageProvider

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "429 Client Error: Too Many Requests for url: "
            "https://www.alphavantage.co/query?apikey=SECRET_KEY"
        )
        mock_resp.status_code = 429
        mock_get.return_value = mock_resp

        provider = AlphaVantageProvider(api_key="SECRET_KEY")
        with pytest.raises(ProviderError, match="rate limit"):
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))

    @patch("caracal.providers.alphavantage.requests.get")
    def test_fetch_ohlcv_timeout_raises_provider_error(self, mock_get):
        from caracal.providers.alphavantage import AlphaVantageProvider

        mock_get.side_effect = requests.exceptions.Timeout(
            "Connection to alphavantage.co timed out. "
            "(connect timeout=30)"
        )

        provider = AlphaVantageProvider(api_key="SECRET_KEY")
        with pytest.raises(ProviderError, match="[Nn]etwork"):
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))

    @patch("caracal.providers.alphavantage.requests.get")
    def test_fetch_ohlcv_connection_error_raises_provider_error(self, mock_get):
        from caracal.providers.alphavantage import AlphaVantageProvider

        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Failed to establish a new connection"
        )

        provider = AlphaVantageProvider(api_key="SECRET_KEY")
        with pytest.raises(ProviderError, match="[Nn]etwork"):
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))

    @patch("caracal.providers.alphavantage.requests.get")
    def test_fetch_ohlcv_error_does_not_leak_url(self, mock_get):
        from caracal.providers.alphavantage import AlphaVantageProvider

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error for url: "
            "https://www.alphavantage.co/query?apikey=SECRET_KEY"
        )
        mock_resp.status_code = 500
        mock_get.return_value = mock_resp

        provider = AlphaVantageProvider(api_key="SECRET_KEY")
        with pytest.raises(ProviderError) as exc_info:
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))

        error_msg = str(exc_info.value)
        assert "SECRET_KEY" not in error_msg
        assert "alphavantage.co" not in error_msg

    @patch("caracal.providers.alphavantage.requests.get")
    def test_validate_ticker_error_does_not_leak_api_key(self, mock_get):
        from caracal.providers.alphavantage import AlphaVantageProvider

        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Failed to connect to https://www.alphavantage.co/query?apikey=SECRET_KEY"
        )

        provider = AlphaVantageProvider(api_key="SECRET_KEY")
        with pytest.raises(ProviderError) as exc_info:
            provider.validate_ticker("AAPL")

        error_msg = str(exc_info.value)
        assert "SECRET_KEY" not in error_msg

    @patch("caracal.providers.alphavantage.requests.get")
    def test_validate_ticker_http_error_raises_provider_error(self, mock_get):
        from caracal.providers.alphavantage import AlphaVantageProvider

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error"
        )
        mock_get.return_value = mock_resp

        provider = AlphaVantageProvider(api_key="test_key")
        with pytest.raises(ProviderError, match="validation failed"):
            provider.validate_ticker("AAPL")

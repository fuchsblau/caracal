"""Tests for Finnhub market data provider."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from caracal.providers.types import (
    ProviderError,
    TickerNotFoundError,
    assert_ohlcv_schema,
)

_SAMPLE_RESPONSE = {
    "s": "ok",
    "t": [1704153600, 1704240000],  # 2024-01-02, 2024-01-03 UTC
    "o": [100.0, 101.0],
    "h": [105.0, 106.0],
    "l": [99.0, 100.0],
    "c": [104.0, 105.0],
    "v": [1000000, 1100000],
}


class TestFinnhubProvider:
    def test_name(self):
        from caracal.providers.finnhub import FinnhubProvider

        provider = FinnhubProvider(api_key="test_key")
        assert provider.name == "finnhub"

    def test_missing_api_key_raises(self):
        from caracal.providers.finnhub import FinnhubProvider

        with pytest.raises(ProviderError, match="API key"):
            FinnhubProvider()

    @patch("caracal.providers.finnhub.requests.get")
    def test_fetch_ohlcv_success(self, mock_get):
        from caracal.providers.finnhub import FinnhubProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = _SAMPLE_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = FinnhubProvider(api_key="test_key")
        df = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))
        assert len(df) == 2
        assert_ohlcv_schema(df)
        assert df.iloc[0]["close"] == 104.0
        assert isinstance(df.iloc[0]["date"], date)

    @patch("caracal.providers.finnhub.requests.get")
    def test_fetch_ohlcv_uses_unix_timestamps(self, mock_get):
        from caracal.providers.finnhub import FinnhubProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = _SAMPLE_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = FinnhubProvider(api_key="test_key")
        provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 5))

        call_kwargs = mock_get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert isinstance(params["from"], int)
        assert isinstance(params["to"], int)
        assert params["resolution"] == "D"

    @patch("caracal.providers.finnhub.requests.get")
    def test_fetch_ohlcv_no_data_raises(self, mock_get):
        from caracal.providers.finnhub import FinnhubProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"s": "no_data"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = FinnhubProvider(api_key="test_key")
        with pytest.raises(TickerNotFoundError):
            provider.fetch_ohlcv("INVALID", date(2024, 1, 1), date(2024, 1, 5))

    @patch("caracal.providers.finnhub.requests.get")
    def test_validate_ticker_valid(self, mock_get):
        from caracal.providers.finnhub import FinnhubProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = _SAMPLE_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = FinnhubProvider(api_key="test_key")
        assert provider.validate_ticker("AAPL") is True

    @patch("caracal.providers.finnhub.requests.get")
    def test_validate_ticker_invalid(self, mock_get):
        from caracal.providers.finnhub import FinnhubProvider

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"s": "no_data"}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        provider = FinnhubProvider(api_key="test_key")
        assert provider.validate_ticker("INVALID") is False

"""Tests for Massive.com market data provider."""

import sys
from datetime import date
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from caracal.providers.types import (
    ProviderError,
    TickerNotFoundError,
    assert_ohlcv_schema,
)

# Install a fake 'massive' module so that
# ``from massive import RESTClient`` succeeds at import time.
_fake_massive = ModuleType("massive")
_fake_massive.RESTClient = MagicMock()


@pytest.fixture(autouse=True)
def _mock_massive_package(monkeypatch):
    """Ensure the 'massive' package is importable during tests.

    The real package is not installed; we inject a fake module into
    sys.modules so the provider's module-level import succeeds.
    After the test we clean up both the fake package and the cached
    provider module to ensure a fresh import in every test.
    """
    monkeypatch.setitem(sys.modules, "massive", _fake_massive)
    # Clear any previously cached import of the provider module
    # so each test gets a fresh import with the mock in place.
    sys.modules.pop("caracal.providers.massive", None)
    yield
    # Clean up so the provider module is re-imported fresh each test.
    sys.modules.pop("caracal.providers.massive", None)


class TestMassiveProvider:
    def _make_provider(self, api_key="pk_test123"):
        from caracal.providers.massive import MassiveProvider

        with patch("caracal.providers.massive.RESTClient"):
            return MassiveProvider(api_key=api_key)

    def test_name(self):
        provider = self._make_provider()
        assert provider.name == "massive"

    def test_missing_api_key_raises(self):
        from caracal.providers.massive import MassiveProvider

        with patch("caracal.providers.massive.RESTClient"):
            with pytest.raises(ProviderError, match="API key"):
                MassiveProvider()

    @patch("caracal.providers.massive.RESTClient")
    def test_fetch_ohlcv_success(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_agg = MagicMock()
        mock_agg.timestamp = 1704153600000  # 2024-01-02 UTC
        mock_agg.open = 100.0
        mock_agg.high = 105.0
        mock_agg.low = 99.0
        mock_agg.close = 104.0
        mock_agg.volume = 1000000
        mock_client.list_aggs.return_value = iter([mock_agg])

        from caracal.providers.massive import MassiveProvider

        provider = MassiveProvider(api_key="pk_test")
        df = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 3))

        assert len(df) == 1
        assert_ohlcv_schema(df)
        assert df.iloc[0]["close"] == 104.0

    @patch("caracal.providers.massive.RESTClient")
    def test_fetch_ohlcv_empty_raises(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.list_aggs.return_value = iter([])

        from caracal.providers.massive import MassiveProvider

        provider = MassiveProvider(api_key="pk_test")
        with pytest.raises(TickerNotFoundError):
            provider.fetch_ohlcv("INVALID", date(2024, 1, 1), date(2024, 1, 3))

    @patch("caracal.providers.massive.RESTClient")
    def test_fetch_ohlcv_api_error(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.list_aggs.side_effect = Exception("Unauthorized")

        from caracal.providers.massive import MassiveProvider

        provider = MassiveProvider(api_key="pk_test")
        with pytest.raises(ProviderError, match="Unauthorized"):
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 3))

    @patch("caracal.providers.massive.RESTClient")
    def test_validate_ticker_valid(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_details = MagicMock()
        mock_details.ticker = "AAPL"
        mock_client.get_ticker_details.return_value = mock_details

        from caracal.providers.massive import MassiveProvider

        provider = MassiveProvider(api_key="pk_test")
        assert provider.validate_ticker("AAPL") is True

    @patch("caracal.providers.massive.RESTClient")
    def test_validate_ticker_invalid(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.get_ticker_details.side_effect = Exception("Not found")

        from caracal.providers.massive import MassiveProvider

        provider = MassiveProvider(api_key="pk_test")
        assert provider.validate_ticker("INVALID") is False

"""Tests for Interactive Brokers market data provider."""

import sys
from datetime import date
from types import ModuleType
from unittest.mock import MagicMock

import pandas as pd
import pytest

from caracal.providers.types import (
    ProviderError,
    TickerNotFoundError,
    assert_ohlcv_schema,
)

# Install a fake 'ib_async' module so that
# ``from ib_async import IB, Stock, util`` succeeds at import time.
_fake_ib_async = ModuleType("ib_async")
_fake_ib_async.IB = MagicMock()
_fake_ib_async.Stock = MagicMock()
_fake_ib_async.util = MagicMock()


@pytest.fixture(autouse=True)
def _mock_ib_async_package(monkeypatch):
    """Ensure the 'ib_async' package is importable during tests.

    The real package is not installed; we inject a fake module into
    sys.modules so the provider's module-level import succeeds.
    After the test we clean up both the fake package and the cached
    provider module to ensure a fresh import in every test.
    """
    monkeypatch.setitem(sys.modules, "ib_async", _fake_ib_async)
    # Clear any previously cached import of the provider module
    # so each test gets a fresh import with the mock in place.
    sys.modules.pop("caracal.providers.ibkr", None)
    yield
    # Clean up so the provider module is re-imported fresh each test.
    sys.modules.pop("caracal.providers.ibkr", None)


class TestIBKRProvider:
    def _make_provider(self, **kwargs):
        from caracal.providers.ibkr import IBKRProvider

        return IBKRProvider(**kwargs)

    def test_name(self):
        provider = self._make_provider()
        assert provider.name == "ibkr"

    def test_default_config(self):
        provider = self._make_provider()
        assert provider._host == "127.0.0.1"
        assert provider._port == 7497
        assert provider._client_id == 1

    def test_custom_config(self):
        provider = self._make_provider(
            host="192.168.1.10", port="4001", client_id="2"
        )
        assert provider._host == "192.168.1.10"
        assert provider._port == 4001
        assert provider._client_id == 2

    def test_fetch_ohlcv_success(self):
        from caracal.providers.ibkr import IBKRProvider

        mock_ib = MagicMock()
        mock_ib.isConnected.return_value = False

        # Build a DataFrame that mimics util.df(bars) output,
        # including extra columns that IBKRProvider must strip.
        bar_df = pd.DataFrame(
            [
                {
                    "date": "2024-01-02",
                    "open": 100.0,
                    "high": 105.0,
                    "low": 99.0,
                    "close": 104.0,
                    "volume": 1_000_000,
                    "barCount": 5000,
                    "average": 102.5,
                },
            ]
        )

        mock_ib.reqHistoricalData.return_value = [MagicMock()]

        from caracal.providers import ibkr as ibkr_mod

        ibkr_mod.util.df.return_value = bar_df

        provider = IBKRProvider()
        provider._ib = mock_ib

        df = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 3))

        assert len(df) == 1
        assert_ohlcv_schema(df)
        assert df.iloc[0]["close"] == 104.0
        # Extra columns must be removed
        assert "barCount" not in df.columns
        assert "average" not in df.columns

    def test_fetch_ohlcv_empty_raises(self):
        from caracal.providers.ibkr import IBKRProvider

        mock_ib = MagicMock()
        mock_ib.isConnected.return_value = False
        mock_ib.reqHistoricalData.return_value = []

        provider = IBKRProvider()
        provider._ib = mock_ib

        with pytest.raises(TickerNotFoundError):
            provider.fetch_ohlcv("INVALID", date(2024, 1, 1), date(2024, 1, 3))

    def test_fetch_ohlcv_api_error(self):
        from caracal.providers.ibkr import IBKRProvider

        mock_ib = MagicMock()
        mock_ib.isConnected.return_value = False
        mock_ib.connect.side_effect = ConnectionRefusedError("refused")

        provider = IBKRProvider()
        provider._ib = mock_ib

        with pytest.raises(ProviderError, match="TWS"):
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 3))

    def test_fetch_ohlcv_error_does_not_leak_details(self):
        from caracal.providers.ibkr import IBKRProvider

        mock_ib = MagicMock()
        mock_ib.isConnected.return_value = True
        mock_ib.reqHistoricalData.side_effect = Exception(
            "TWS error 162: Historical Market Data not subscribed for SMART/USD"
        )

        provider = IBKRProvider()
        provider._ib = mock_ib

        with pytest.raises(ProviderError) as exc_info:
            provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 12, 31))
        assert "162" not in str(exc_info.value)
        assert "not subscribed" not in str(exc_info.value)

    def test_connection_reuse(self):
        from caracal.providers.ibkr import IBKRProvider

        mock_ib = MagicMock()
        # First call: not connected; second call: already connected
        mock_ib.isConnected.side_effect = [False, True]
        mock_ib.reqHistoricalData.return_value = [MagicMock()]

        bar_df = pd.DataFrame(
            [
                {
                    "date": "2024-01-02",
                    "open": 100.0,
                    "high": 105.0,
                    "low": 99.0,
                    "close": 104.0,
                    "volume": 1_000_000,
                },
            ]
        )

        from caracal.providers import ibkr as ibkr_mod

        ibkr_mod.util.df.return_value = bar_df

        provider = IBKRProvider()
        provider._ib = mock_ib

        provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 3))
        provider.fetch_ohlcv("MSFT", date(2024, 1, 1), date(2024, 1, 3))

        # connect() should only have been called once (first fetch)
        mock_ib.connect.assert_called_once()

    def test_validate_ticker_valid(self):
        from caracal.providers.ibkr import IBKRProvider

        mock_ib = MagicMock()
        mock_ib.isConnected.return_value = True

        mock_contract = MagicMock()
        mock_contract.conId = 265598
        mock_ib.qualifyContracts.return_value = [mock_contract]

        provider = IBKRProvider()
        provider._ib = mock_ib

        assert provider.validate_ticker("AAPL") is True

    def test_validate_ticker_invalid(self):
        from caracal.providers.ibkr import IBKRProvider

        mock_ib = MagicMock()
        mock_ib.isConnected.return_value = True
        mock_ib.qualifyContracts.return_value = []

        provider = IBKRProvider()
        provider._ib = mock_ib

        assert provider.validate_ticker("INVALID") is False

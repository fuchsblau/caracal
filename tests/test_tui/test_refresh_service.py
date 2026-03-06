"""Tests for RefreshService."""

import logging
from datetime import date, timedelta

import pandas as pd
import pytest

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui.services.refresh_service import RefreshService


def _store_ohlcv(storage, ticker, days=31, trend="flat"):
    """Store synthetic OHLCV data for testing."""
    base_price = 100.0
    rows = []
    for i in range(days):
        if trend == "up":
            price = base_price + i * 2
        elif trend == "down":
            price = base_price - i * 2
        else:
            price = base_price + (i % 3 - 1)
        d = date.today() - timedelta(days=days - i)
        rows.append({
            "date": d,
            "open": price - 0.5,
            "high": price + 1,
            "low": price - 1,
            "close": price,
            "volume": 1000000,
        })
    df = pd.DataFrame(rows)
    storage.store_ohlcv(ticker, df)


@pytest.fixture
def storage():
    s = DuckDBStorage(":memory:")
    yield s
    s.close()


@pytest.fixture
def config():
    return CaracalConfig(db_path=":memory:")


@pytest.fixture
def service(storage, config):
    return RefreshService(config=config, storage=storage)


class TestGetLastFetchTime:
    def test_returns_none_for_memory_db(self, service):
        assert service.get_last_fetch_time() is None

    def test_returns_datetime_for_file_db(self, tmp_path):
        db_file = str(tmp_path / "test.db")
        config = CaracalConfig(db_path=db_file)
        storage = DuckDBStorage(db_file)
        svc = RefreshService(config=config, storage=storage)
        storage.create_watchlist("tech")
        result = svc.get_last_fetch_time()
        assert result is not None
        assert len(result) == 19  # YYYY-MM-DD HH:MM:SS
        storage.close()


class TestRefreshWatchlist:
    def test_refresh_returns_rows(self, service, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "AAPL")
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "open": [150.0, 152.0],
            "high": [155.0, 156.0],
            "low": [149.0, 151.0],
            "close": [153.0, 155.0],
            "volume": [1000000, 1100000],
        })
        storage.store_ohlcv("AAPL", df)
        rows = service.refresh_watchlist("tech")
        assert len(rows) == 1
        assert rows[0]["ticker"] == "AAPL"


class TestRefreshWatchlistLive:
    def test_falls_back_on_provider_error(self, service, storage, caplog, monkeypatch):
        storage.create_watchlist("test")
        storage.add_to_watchlist("test", "AAPL")
        _store_ohlcv(storage, "AAPL", days=5)

        def _broken_get_provider(*args, **kwargs):
            raise RuntimeError("provider unavailable")

        monkeypatch.setattr(
            "caracal.providers.get_provider", _broken_get_provider
        )
        with caplog.at_level(logging.WARNING, logger="caracal"):
            rows = service.refresh_watchlist_live("test")
        assert len(rows) == 1
        assert rows[0]["ticker"] == "AAPL"

    def test_logs_per_ticker_failure(self, service, storage, caplog, monkeypatch):
        storage.create_watchlist("test")
        storage.add_to_watchlist("test", "AAPL")
        _store_ohlcv(storage, "AAPL", days=5)

        class _BrokenProvider:
            def fetch_ohlcv(self, ticker, start, end):
                raise RuntimeError("network error")

        monkeypatch.setattr(
            "caracal.providers.get_provider", lambda *a, **kw: _BrokenProvider()
        )
        with caplog.at_level(logging.WARNING, logger="caracal"):
            service.refresh_watchlist_live("test")
        assert any(
            "fetch" in r.message.lower() for r in caplog.records
        )


class TestFetchTickerNames:
    def test_logs_import_error(self, service, caplog, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def _block_yfinance(name, *args, **kwargs):
            if name == "yfinance":
                raise ImportError("No module named 'yfinance'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _block_yfinance)
        with caplog.at_level(logging.DEBUG, logger="caracal"):
            service._fetch_ticker_names(["AAPL"])
        assert any(
            "yfinance" in r.message.lower() for r in caplog.records
        )

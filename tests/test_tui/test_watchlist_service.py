"""Tests for WatchlistService."""

import pytest

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage, StorageError
from caracal.tui.services.watchlist_service import WatchlistService


@pytest.fixture
def storage():
    s = DuckDBStorage(":memory:")
    yield s
    s.close()


@pytest.fixture
def service(storage):
    config = CaracalConfig(db_path=":memory:")
    return WatchlistService(config=config, storage=storage)


class TestWatchlistService:
    def test_create_and_list(self, service):
        service.create_watchlist("test")
        names = service.get_watchlist_names()
        assert "test" in names

    def test_list_empty(self, service):
        assert service.get_watchlist_names() == []

    def test_list_sorted(self, service):
        service.create_watchlist("zeta")
        service.create_watchlist("alpha")
        assert service.get_watchlist_names() == ["alpha", "zeta"]

    def test_delete_watchlist(self, service):
        service.create_watchlist("test")
        service.delete_watchlist("test")
        assert "test" not in service.get_watchlist_names()

    def test_delete_nonexistent_raises(self, service):
        with pytest.raises(StorageError):
            service.delete_watchlist("nope")

    def test_create_duplicate_raises(self, service):
        service.create_watchlist("dup")
        with pytest.raises(StorageError):
            service.create_watchlist("dup")

    def test_add_and_get_tickers(self, service):
        service.create_watchlist("test")
        added, dupes = service.add_to_watchlist("test", ["AAPL", "MSFT"])
        assert added == ["AAPL", "MSFT"]
        assert dupes == []

    def test_duplicate_tickers(self, service):
        service.create_watchlist("test")
        service.add_to_watchlist("test", ["AAPL"])
        added, dupes = service.add_to_watchlist("test", ["AAPL", "MSFT"])
        assert added == ["MSFT"]
        assert dupes == ["AAPL"]

    def test_remove_ticker(self, service):
        service.create_watchlist("test")
        service.add_to_watchlist("test", ["AAPL"])
        service.remove_from_watchlist("test", "AAPL")

    def test_remove_nonexistent_ticker_raises(self, service):
        service.create_watchlist("test")
        with pytest.raises(StorageError):
            service.remove_from_watchlist("test", "NOPE")

    def test_add_to_nonexistent_watchlist_raises(self, service):
        with pytest.raises(StorageError):
            service.add_to_watchlist("nope", ["AAPL"])

    def test_get_watchlists_returns_dicts(self, service):
        service.create_watchlist("test")
        result = service.get_watchlists()
        assert len(result) >= 1
        wl = next(w for w in result if w["name"] == "test")
        assert "name" in wl
        assert "ticker_count" in wl

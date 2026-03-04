"""Tests for watchlist storage operations."""

import pytest

from caracal.providers.types import StorageError


class TestCreateWatchlist:
    def test_create_watchlist(self, storage):
        storage.create_watchlist("tech")
        assert storage.watchlist_exists("tech")

    def test_create_duplicate_raises(self, storage):
        storage.create_watchlist("tech")
        with pytest.raises(StorageError, match="already exists"):
            storage.create_watchlist("tech")


class TestDeleteWatchlist:
    def test_delete_watchlist(self, storage):
        storage.create_watchlist("tech")
        storage.delete_watchlist("tech")
        assert not storage.watchlist_exists("tech")

    def test_delete_nonexistent_raises(self, storage):
        with pytest.raises(StorageError, match="not found"):
            storage.delete_watchlist("nonexistent")

    def test_delete_removes_items(self, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "AAPL")
        storage.delete_watchlist("tech")
        assert not storage.watchlist_exists("tech")


class TestAddToWatchlist:
    def test_add_ticker(self, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "AAPL")
        items = storage.get_watchlist_items("tech")
        assert items == ["AAPL"]

    def test_add_multiple_tickers(self, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "AAPL")
        storage.add_to_watchlist("tech", "MSFT")
        items = storage.get_watchlist_items("tech")
        assert sorted(items) == ["AAPL", "MSFT"]

    def test_add_duplicate_raises(self, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "AAPL")
        with pytest.raises(StorageError, match="already in"):
            storage.add_to_watchlist("tech", "AAPL")

    def test_add_to_nonexistent_raises(self, storage):
        with pytest.raises(StorageError, match="not found"):
            storage.add_to_watchlist("nonexistent", "AAPL")


class TestRemoveFromWatchlist:
    def test_remove_ticker(self, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "AAPL")
        storage.remove_from_watchlist("tech", "AAPL")
        items = storage.get_watchlist_items("tech")
        assert items == []

    def test_remove_nonexistent_ticker_raises(self, storage):
        storage.create_watchlist("tech")
        with pytest.raises(StorageError, match="not in"):
            storage.remove_from_watchlist("tech", "AAPL")

    def test_remove_from_nonexistent_watchlist_raises(self, storage):
        with pytest.raises(StorageError, match="not found"):
            storage.remove_from_watchlist("nonexistent", "AAPL")


class TestGetWatchlists:
    def test_list_empty(self, storage):
        result = storage.get_watchlists()
        assert result == []

    def test_list_with_items(self, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "AAPL")
        storage.add_to_watchlist("tech", "MSFT")
        storage.create_watchlist("energy")
        result = storage.get_watchlists()
        assert len(result) == 2
        names = [w["name"] for w in result]
        assert "tech" in names
        assert "energy" in names
        tech = next(w for w in result if w["name"] == "tech")
        assert tech["ticker_count"] == 2
        energy = next(w for w in result if w["name"] == "energy")
        assert energy["ticker_count"] == 0


class TestGetWatchlistItems:
    def test_get_items(self, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "AAPL")
        storage.add_to_watchlist("tech", "MSFT")
        items = storage.get_watchlist_items("tech")
        assert sorted(items) == ["AAPL", "MSFT"]

    def test_get_items_nonexistent_raises(self, storage):
        with pytest.raises(StorageError, match="not found"):
            storage.get_watchlist_items("nonexistent")


class TestWatchlistExists:
    def test_exists_true(self, storage):
        storage.create_watchlist("tech")
        assert storage.watchlist_exists("tech") is True

    def test_exists_false(self, storage):
        assert storage.watchlist_exists("nonexistent") is False

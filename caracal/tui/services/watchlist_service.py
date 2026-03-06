"""Watchlist CRUD operations."""

from __future__ import annotations

import logging

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage

logger = logging.getLogger("caracal")


class WatchlistService:
    """Watchlist CRUD -- extracted from DataService."""

    def __init__(self, config: CaracalConfig, storage: DuckDBStorage) -> None:
        self._storage = storage

    def get_watchlist_names(self) -> list[str]:
        """Return sorted list of watchlist names."""
        watchlists = self._storage.get_watchlists()
        return sorted(wl["name"] for wl in watchlists)

    def get_watchlists(self) -> list[dict]:
        """Return all watchlists with name, created_at, ticker_count."""
        return self._storage.get_watchlists()

    def create_watchlist(self, name: str) -> None:
        """Create a new watchlist. Raises StorageError if name exists."""
        self._storage.create_watchlist(name)

    def delete_watchlist(self, name: str) -> None:
        """Delete a watchlist and its items. Raises StorageError if not found."""
        self._storage.delete_watchlist(name)

    def add_to_watchlist(
        self, name: str, tickers: list[str]
    ) -> tuple[list[str], list[str]]:
        """Add tickers to a watchlist. Returns (added, duplicates).

        Raises StorageError if watchlist does not exist.
        """
        existing = set(self._storage.get_watchlist_items(name))
        added: list[str] = []
        duplicates: list[str] = []
        for ticker in tickers:
            if ticker in existing:
                duplicates.append(ticker)
            else:
                self._storage.add_to_watchlist(name, ticker)
                added.append(ticker)
                existing.add(ticker)
        return added, duplicates

    def remove_from_watchlist(self, name: str, ticker: str) -> None:
        """Remove a ticker from a watchlist.

        Raises StorageError if watchlist or ticker not found.
        """
        self._storage.remove_from_watchlist(name, ticker)

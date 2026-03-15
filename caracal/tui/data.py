"""Data access facade for TUI screens -- delegates to focused services."""

from __future__ import annotations

from caracal import __version__
from caracal.config import CONFIG_PATH, CaracalConfig
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui.services.analysis_service import (
    CATEGORY_ORDER,
    INDICATOR_CATEGORIES,
    INDICATOR_DISPLAY_NAMES,
    AnalysisService,
)
from caracal.tui.services.news_service import NewsService
from caracal.tui.services.refresh_service import RefreshService
from caracal.tui.services.watchlist_service import WatchlistService

# Re-export registries so existing imports from caracal.tui.data keep working
__all__ = [
    "CATEGORY_ORDER",
    "INDICATOR_CATEGORIES",
    "INDICATOR_DISPLAY_NAMES",
    "DataService",
]


class DataService:
    """Thin facade -- screens use this, delegates to focused services.

    Backwards-compatible: all public methods and internal helpers
    (_interpret_indicator, _calculate_vote_counts, _fetch_ticker_names)
    are preserved for existing callers.
    """

    def __init__(
        self,
        config: CaracalConfig,
        storage: DuckDBStorage | None = None,
    ) -> None:
        self.config = config
        self._storage = storage or DuckDBStorage(config.db_path)
        self._owns_storage = storage is None
        self.watchlists = WatchlistService(config, self._storage)
        self.analysis = AnalysisService(config, self._storage)
        self.refresh = RefreshService(config, self._storage)
        self.news = NewsService(config, self._storage)

    def close(self) -> None:
        if self._owns_storage:
            self._storage.close()

    # -- Watchlist delegates --------------------------------------------------

    def get_watchlist_names(self) -> list[str]:
        """Return sorted list of watchlist names."""
        return self.watchlists.get_watchlist_names()

    def get_watchlists(self) -> list[dict]:
        """Return all watchlists with name, created_at, ticker_count."""
        return self.watchlists.get_watchlists()

    def create_watchlist(self, name: str) -> None:
        """Create a new watchlist. Raises StorageError if name exists."""
        self.watchlists.create_watchlist(name)

    def delete_watchlist(self, name: str) -> None:
        """Delete a watchlist and its items. Raises StorageError if not found."""
        self.watchlists.delete_watchlist(name)

    def add_to_watchlist(
        self, name: str, tickers: list[str]
    ) -> tuple[list[str], list[str]]:
        """Add tickers to a watchlist. Returns (added, duplicates)."""
        return self.watchlists.add_to_watchlist(name, tickers)

    def remove_from_watchlist(self, name: str, ticker: str) -> None:
        """Remove a ticker from a watchlist."""
        self.watchlists.remove_from_watchlist(name, ticker)

    # -- Analysis delegates ---------------------------------------------------

    def get_watchlist_overview(self, name: str) -> list[dict]:
        """Return overview rows for a watchlist."""
        return self.analysis.get_watchlist_overview(name)

    def get_stock_detail(self, ticker: str) -> dict:
        """Return full detail for a single stock."""
        return self.analysis.get_stock_detail(ticker)

    def _interpret_indicator(
        self, key: str, value: float | None, *, close: float, indicators: dict
    ) -> tuple[str | None, str | None]:
        """Delegate to AnalysisService (backwards compat)."""
        return self.analysis._interpret_indicator(
            key, value, close=close, indicators=indicators
        )

    def _calculate_vote_counts(self, df) -> dict | None:
        """Delegate to AnalysisService (backwards compat)."""
        return self.analysis._calculate_vote_counts(df)

    # -- Refresh delegates ----------------------------------------------------

    def refresh_watchlist(self, name: str) -> list[dict]:
        """Re-read watchlist data from storage (no provider fetch)."""
        return self.refresh.refresh_watchlist(name)

    def refresh_watchlist_live(self, name: str) -> list[dict]:
        """Fetch fresh data from provider, recalculate, return overview."""
        return self.refresh.refresh_watchlist_live(name)

    def get_last_fetch_time(self) -> str | None:
        """Return the last time data was written to the DB."""
        return self.refresh.get_last_fetch_time()

    def _fetch_ticker_names(self, tickers: list[str]) -> None:
        """Delegate to RefreshService (backwards compat)."""
        self.refresh._fetch_ticker_names(tickers)

    # -- News delegates -------------------------------------------------------

    def get_news(self, limit: int = 50) -> list[dict]:
        """Return recent news items with relative timestamps."""
        return self.news.get_recent_news(limit=limit)

    # -- App info -------------------------------------------------------------

    def get_app_info(self) -> dict:
        """Return app metadata for the info screen."""
        return {
            "version": __version__,
            "provider": self.config.default_provider,
            "config_path": str(CONFIG_PATH),
            "db_path": self.config.db_path,
        }

"""Data refresh and provider fetch operations."""

from __future__ import annotations

import logging

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage

logger = logging.getLogger("caracal")


class RefreshService:
    """Provider fetch and data refresh -- extracted from DataService."""

    def __init__(self, config: CaracalConfig, storage: DuckDBStorage) -> None:
        self._config = config
        self._storage = storage

    def get_last_fetch_time(self) -> str | None:
        """Return the last time data was written to the DB.

        Uses the DB file's modification time as a proxy for when
        provider data was last fetched.  Returns None for in-memory DBs.
        """
        import os
        from datetime import datetime

        db_path = os.path.expanduser(self._config.db_path)
        if db_path == ":memory:" or not os.path.exists(db_path):
            return None
        mtime = os.path.getmtime(db_path)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

    def refresh_watchlist(self, name: str) -> list[dict]:
        """Re-read watchlist data from storage (no provider fetch).

        For actual live fetch, use refresh_watchlist_live() in a worker.
        """
        # Import here to avoid circular dependency at module level
        from caracal.tui.services.analysis_service import AnalysisService

        analysis = AnalysisService(self._config, self._storage)
        return analysis.get_watchlist_overview(name)

    def refresh_watchlist_live(self, name: str) -> list[dict]:
        """Fetch fresh data from provider, recalculate, return overview.

        For use in background workers -- calls provider, stores results,
        then returns fresh overview.  Falls back to cached data on any
        provider error.
        """
        from datetime import date, timedelta

        from caracal.providers import get_provider

        tickers = self._storage.get_watchlist_items(name)

        try:
            provider_kwargs = {}
            provider_name = self._config.default_provider
            if provider_name in self._config.providers:
                provider_kwargs = self._config.providers[provider_name]
            provider = get_provider(provider_name, **provider_kwargs)

            period_days = {
                "1y": 365, "6mo": 182, "3mo": 91, "1mo": 30, "5y": 1825,
            }
            days = period_days.get(self._config.default_period, 365)
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            for ticker in tickers:
                try:
                    df = provider.fetch_ohlcv(ticker, start_date, end_date)
                    if not df.empty:
                        self._storage.store_ohlcv(ticker, df)
                except Exception:
                    logger.warning(
                        "Failed to fetch %s, using cached data",
                        ticker,
                        exc_info=True,
                    )
        except Exception:
            logger.warning(
                "Provider unavailable, using cached data", exc_info=True
            )

        # Cache company names independently of provider fetch
        self._fetch_ticker_names(tickers)

        return self.refresh_watchlist(name)

    def _fetch_ticker_names(self, tickers: list[str]) -> None:
        """Fetch and cache company names for tickers missing a name."""
        try:
            import yfinance as yf
        except ImportError:
            logger.debug("yfinance not installed, skipping ticker name fetch")
            return
        for ticker in tickers:
            if self._storage.get_ticker_name(ticker):
                continue
            try:
                info = yf.Ticker(ticker).info
                name = info.get("shortName") or info.get("longName")
                if name:
                    self._storage.store_ticker_name(ticker, name)
            except Exception:
                logger.debug(
                    "Failed to fetch name for %s", ticker, exc_info=True
                )

"""Data access facade for TUI screens."""

from __future__ import annotations

from caracal import __version__
from caracal.analysis.entry_points import calculate_entry_signal
from caracal.config import CONFIG_PATH, CaracalConfig
from caracal.output.precision import PERCENT_DECIMALS, PRICE_DECIMALS
from caracal.storage.duckdb import DuckDBStorage


class DataService:
    """Facade over Storage, Provider, and Analysis modules.

    Screens use only this class for data access — no direct
    DuckDB or Provider imports in screen code.
    """

    def __init__(
        self,
        config: CaracalConfig,
        storage: DuckDBStorage | None = None,
    ) -> None:
        self.config = config
        self._storage = storage or DuckDBStorage(config.db_path)
        self._owns_storage = storage is None

    def close(self) -> None:
        if self._owns_storage:
            self._storage.close()

    # -- Watchlist data -------------------------------------------------------

    def get_watchlist_names(self) -> list[str]:
        """Return sorted list of watchlist names."""
        watchlists = self._storage.get_watchlists()
        return sorted(wl["name"] for wl in watchlists)

    def get_watchlist_overview(self, name: str) -> list[dict]:
        """Return overview rows for a watchlist.

        Each row: {ticker, close, change_pct, signal}
        Uses cached OHLCV data from DuckDB — no provider calls.
        """
        tickers = self._storage.get_watchlist_items(name)
        rows = []
        for ticker in tickers:
            row = self._build_ticker_row(ticker)
            rows.append(row)
        return rows

    def _build_ticker_row(self, ticker: str) -> dict:
        """Build a single watchlist row from cached data."""
        df = self._storage.get_ohlcv(ticker)

        if df.empty or len(df) < 1:
            return {
                "ticker": ticker,
                "close": None,
                "change_pct": None,
                "signal": "N/A",
            }

        close = round(float(df.iloc[-1]["close"]), PRICE_DECIMALS)
        change_pct = None
        if len(df) >= 2:
            prev_close = float(df.iloc[-2]["close"])
            if prev_close != 0:
                change_pct = round(
                    ((close - prev_close) / prev_close) * 100,
                    PERCENT_DECIMALS,
                )

        signal = "N/A"
        if len(df) >= 30:
            result = calculate_entry_signal(df)
            signal = result["signal"]

        return {
            "ticker": ticker,
            "close": close,
            "change_pct": change_pct,
            "signal": signal,
        }

    def create_watchlist(self, name: str) -> None:
        """Create a new watchlist. Raises StorageError if name exists."""
        self._storage.create_watchlist(name)

    def delete_watchlist(self, name: str) -> None:
        """Delete a watchlist and its items. Raises StorageError if not found."""
        self._storage.delete_watchlist(name)

    def get_watchlists(self) -> list[dict]:
        """Return all watchlists with name, created_at, ticker_count."""
        return self._storage.get_watchlists()

    def refresh_watchlist(self, name: str) -> list[dict]:
        """Re-read watchlist data from storage (no provider fetch).

        For actual live fetch, use refresh_watchlist_live() in a worker.
        """
        return self.get_watchlist_overview(name)

    # -- Stock detail ---------------------------------------------------------

    def get_stock_detail(self, ticker: str) -> dict:
        """Return full detail for a single stock.

        Returns: {ticker, close, change_pct, signal, confidence,
                  indicators, ohlcv}
        """
        df = self._storage.get_ohlcv(ticker)

        if df.empty:
            return {
                "ticker": ticker,
                "close": None,
                "change_pct": None,
                "signal": "N/A",
                "confidence": 0.0,
                "indicators": {},
                "ohlcv": [],
            }

        close = round(float(df.iloc[-1]["close"]), PRICE_DECIMALS)
        change_pct = None
        if len(df) >= 2:
            prev_close = float(df.iloc[-2]["close"])
            if prev_close != 0:
                change_pct = round(
                    ((close - prev_close) / prev_close) * 100,
                    PERCENT_DECIMALS,
                )

        result = calculate_entry_signal(df)

        # Last N days of OHLCV for the table
        tail = df.tail(10)
        ohlcv_rows = []
        for _, row in tail.iterrows():
            ohlcv_rows.append({
                "date": (
                    str(row["date"].date())
                    if hasattr(row["date"], "date")
                    else str(row["date"])
                ),
                "open": round(float(row["open"]), PRICE_DECIMALS),
                "high": round(float(row["high"]), PRICE_DECIMALS),
                "low": round(float(row["low"]), PRICE_DECIMALS),
                "close": round(float(row["close"]), PRICE_DECIMALS),
                "volume": int(row["volume"]),
            })

        return {
            "ticker": ticker,
            "close": close,
            "change_pct": change_pct,
            "signal": result["signal"],
            "confidence": result["confidence"],
            "indicators": result["indicators"],
            "ohlcv": ohlcv_rows,
        }

    # -- App info -------------------------------------------------------------

    def get_app_info(self) -> dict:
        """Return app metadata for the info screen."""
        return {
            "version": __version__,
            "provider": self.config.default_provider,
            "config_path": str(CONFIG_PATH),
            "db_path": self.config.db_path,
        }

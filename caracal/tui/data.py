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

        Each row: {ticker, close, change_pct, signal, confidence, rsi,
                   macd_interpretation, bb_position}
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
        name = self._storage.get_ticker_name(ticker) or ticker
        df = self._storage.get_ohlcv(ticker)

        if df.empty or len(df) < 1:
            return {
                "ticker": ticker,
                "name": name,
                "close": None,
                "change_pct": None,
                "signal": "N/A",
                "confidence": None,
                "rsi": None,
                "macd_interpretation": None,
                "bb_position": None,
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
        confidence = None
        rsi = None
        macd_interpretation = None
        bb_position = None

        if len(df) >= 30:
            result = calculate_entry_signal(df)
            signal = result["signal"]
            confidence = result["confidence"]

            indicators = result["indicators"]

            # RSI value
            rsi_val = indicators.get("rsi_14")
            if rsi_val is not None:
                rsi = round(rsi_val, PERCENT_DECIMALS)

            # MACD interpretation: bullish if MACD > signal line
            macd_val = indicators.get("macd")
            macd_sig = indicators.get("macd_signal")
            if macd_val is not None and macd_sig is not None:
                macd_interpretation = "bull" if macd_val > macd_sig else "bear"

            # Bollinger position: where is price relative to bands
            bb_upper = indicators.get("bollinger_upper")
            bb_lower = indicators.get("bollinger_lower")
            if bb_upper is not None and bb_lower is not None:
                band_width = bb_upper - bb_lower
                if band_width > 0:
                    position = (close - bb_lower) / band_width
                    if position > 1.0:
                        bb_position = "overbought"
                    elif position < 0.0:
                        bb_position = "oversold"
                    else:
                        bb_position = "neutral"

        return {
            "ticker": ticker,
            "name": name,
            "close": close,
            "change_pct": change_pct,
            "signal": signal,
            "confidence": confidence,
            "rsi": rsi,
            "macd_interpretation": macd_interpretation,
            "bb_position": bb_position,
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

    def refresh_watchlist_live(self, name: str) -> list[dict]:
        """Fetch fresh data from provider, recalculate, return overview.

        For use in background workers — calls provider, stores results,
        then returns fresh overview.  Falls back to cached data on any
        provider error.
        """
        from datetime import date, timedelta

        from caracal.providers import get_provider

        tickers = self._storage.get_watchlist_items(name)

        try:
            provider_kwargs = {}
            provider_name = self.config.default_provider
            if provider_name in self.config.providers:
                provider_kwargs = self.config.providers[provider_name]
            provider = get_provider(provider_name, **provider_kwargs)

            period_days = {
                "1y": 365, "6mo": 182, "3mo": 91, "1mo": 30, "5y": 1825,
            }
            days = period_days.get(self.config.default_period, 365)
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            for ticker in tickers:
                try:
                    df = provider.fetch_ohlcv(ticker, start_date, end_date)
                    if not df.empty:
                        self._storage.store_ohlcv(ticker, df)
                except Exception:
                    pass  # Keep cached data on provider failure

            # Cache company names (best-effort)
            self._fetch_ticker_names(tickers)
        except Exception:
            pass  # Fall back to cached data if provider unavailable

        return self.get_watchlist_overview(name)

    def _fetch_ticker_names(self, tickers: list[str]) -> None:
        """Fetch and cache company names for tickers missing a name."""
        try:
            import yfinance as yf
        except ImportError:
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
                pass

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

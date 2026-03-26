"""DuckDB storage implementation."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from types import TracebackType

import duckdb
import pandas as pd

from caracal.providers.types import StorageError

logger = logging.getLogger("caracal")


class DuckDBStorage:
    """DuckDB-based storage for OHLCV and indicator data."""

    def __init__(self, db_path: str = "~/.caracal/caracal.db") -> None:
        try:
            if db_path != ":memory:":
                resolved = Path(db_path).expanduser()
                resolved.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                resolved.parent.chmod(0o700)
                db_path = str(resolved)
            self._conn = duckdb.connect(db_path)
            if db_path != ":memory:" and resolved.exists():
                resolved.chmod(0o600)
        except duckdb.Error as e:
            raise StorageError(f"Failed to connect to DuckDB: {e}") from e
        self._init_schema()

    # -- context manager --------------------------------------------------

    def __enter__(self) -> DuckDBStorage:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    # -- schema -----------------------------------------------------------

    def _init_schema(self) -> None:
        """Run schema migrations."""
        from caracal.storage.migrations import run_migrations

        try:
            run_migrations(self._conn)
        except duckdb.Error as e:
            raise StorageError(f"Failed to initialise schema: {e}") from e

    # -- OHLCV ------------------------------------------------------------

    def store_ohlcv(self, ticker: str, df: pd.DataFrame) -> int:
        """Store OHLCV data with upsert semantics. Returns row count."""
        if df.empty:
            return 0
        staging = df.copy()
        staging["ticker"] = ticker
        try:
            self._conn.register("_staging_ohlcv", staging)
            try:
                self._conn.execute("""
                    INSERT OR REPLACE INTO ohlcv
                        (ticker, date, open, high, low, close, volume)
                    SELECT ticker, date, open, high, low, close, volume
                    FROM _staging_ohlcv
                """)
            finally:
                self._conn.unregister("_staging_ohlcv")
        except duckdb.Error as e:
            raise StorageError(f"Failed to store OHLCV data: {e}") from e
        return len(df)

    def get_ohlcv(
        self,
        ticker: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> pd.DataFrame:
        """Retrieve OHLCV data with optional date range filter."""
        try:
            query = (
                "SELECT date, open, high, low, close, volume"
                " FROM ohlcv WHERE ticker = ?"
            )
            params: list = [ticker]
            if start_date is not None:
                query += " AND date >= ?"
                params.append(start_date)
            if end_date is not None:
                query += " AND date <= ?"
                params.append(end_date)
            query += " ORDER BY date"
            return self._conn.execute(query, params).fetchdf()
        except duckdb.Error as e:
            raise StorageError(f"Failed to get OHLCV data: {e}") from e

    def get_latest_date(self, ticker: str) -> date | None:
        """Return the latest date for a ticker, or None if no data."""
        try:
            result = self._conn.execute(
                "SELECT MAX(date) FROM ohlcv WHERE ticker = ?", [ticker]
            ).fetchone()
            if result is None or result[0] is None:
                return None
            val = result[0]
            if isinstance(val, date):
                return val
            return pd.Timestamp(val).date()
        except duckdb.Error as e:
            raise StorageError(f"Failed to get latest date: {e}") from e

    # -- Indicators -------------------------------------------------------

    def store_indicators(self, ticker: str, df: pd.DataFrame) -> int:
        """Store indicator data with upsert semantics. Returns row count."""
        if df.empty:
            return 0
        staging = df.copy()
        staging["ticker"] = ticker
        try:
            self._conn.register("_staging_indicators", staging)
            try:
                self._conn.execute("""
                    INSERT OR REPLACE INTO indicators
                        (ticker, date, name, value)
                    SELECT ticker, date, name, value
                    FROM _staging_indicators
                """)
            finally:
                self._conn.unregister("_staging_indicators")
        except duckdb.Error as e:
            raise StorageError(f"Failed to store indicators: {e}") from e
        return len(df)

    def get_indicators(
        self, ticker: str, names: list[str] | None = None
    ) -> pd.DataFrame:
        """Retrieve indicators with optional name filter."""
        try:
            query = "SELECT date, name, value FROM indicators WHERE ticker = ?"
            params: list = [ticker]
            if names is not None:
                placeholders = ", ".join(["?"] * len(names))
                query += f" AND name IN ({placeholders})"
                params.extend(names)
            query += " ORDER BY date, name"
            return self._conn.execute(query, params).fetchdf()
        except duckdb.Error as e:
            raise StorageError(f"Failed to get indicators: {e}") from e

    # -- Watchlists -------------------------------------------------------

    def create_watchlist(self, name: str) -> None:
        """Create a named watchlist."""
        try:
            if self.watchlist_exists(name):
                raise StorageError(f"Watchlist '{name}' already exists")
            self._conn.execute("INSERT INTO watchlists (name) VALUES (?)", [name])
        except StorageError:
            raise
        except duckdb.Error as e:
            raise StorageError(f"Failed to create watchlist: {e}") from e

    def delete_watchlist(self, name: str) -> None:
        """Delete a watchlist and all its items."""
        try:
            if not self.watchlist_exists(name):
                raise StorageError(f"Watchlist '{name}' not found")
            self._conn.execute(
                "DELETE FROM watchlist_items WHERE watchlist_name = ?", [name]
            )
            self._conn.execute("DELETE FROM watchlists WHERE name = ?", [name])
        except StorageError:
            raise
        except duckdb.Error as e:
            raise StorageError(f"Failed to delete watchlist: {e}") from e

    def get_watchlists(self) -> list[dict]:
        """Return all watchlists with ticker count."""
        try:
            result = self._conn.execute("""
                SELECT w.name, w.created_at,
                       COUNT(wi.ticker) AS ticker_count
                FROM watchlists w
                LEFT JOIN watchlist_items wi ON w.name = wi.watchlist_name
                GROUP BY w.name, w.created_at
                ORDER BY w.name
            """).fetchall()
            return [
                {
                    "name": row[0],
                    "created_at": row[1],
                    "ticker_count": row[2],
                }
                for row in result
            ]
        except duckdb.Error as e:
            raise StorageError(f"Failed to get watchlists: {e}") from e

    def add_to_watchlist(self, name: str, ticker: str) -> None:
        """Add a ticker to a watchlist."""
        try:
            if not self.watchlist_exists(name):
                raise StorageError(f"Watchlist '{name}' not found")
            existing = self._conn.execute(
                "SELECT 1 FROM watchlist_items WHERE watchlist_name = ? AND ticker = ?",
                [name, ticker],
            ).fetchone()
            if existing:
                raise StorageError(f"Ticker '{ticker}' already in watchlist '{name}'")
            self._conn.execute(
                "INSERT INTO watchlist_items (watchlist_name, ticker) VALUES (?, ?)",
                [name, ticker],
            )
        except StorageError:
            raise
        except duckdb.Error as e:
            raise StorageError(f"Failed to add to watchlist: {e}") from e

    def remove_from_watchlist(self, name: str, ticker: str) -> None:
        """Remove a ticker from a watchlist."""
        try:
            if not self.watchlist_exists(name):
                raise StorageError(f"Watchlist '{name}' not found")
            existing = self._conn.execute(
                "SELECT 1 FROM watchlist_items WHERE watchlist_name = ? AND ticker = ?",
                [name, ticker],
            ).fetchone()
            if not existing:
                raise StorageError(f"Ticker '{ticker}' not in watchlist '{name}'")
            self._conn.execute(
                "DELETE FROM watchlist_items WHERE watchlist_name = ? AND ticker = ?",
                [name, ticker],
            )
        except StorageError:
            raise
        except duckdb.Error as e:
            raise StorageError(f"Failed to remove from watchlist: {e}") from e

    def get_watchlist_items(self, name: str) -> list[str]:
        """Return all tickers in a watchlist."""
        try:
            if not self.watchlist_exists(name):
                raise StorageError(f"Watchlist '{name}' not found")
            result = self._conn.execute(
                "SELECT ticker FROM watchlist_items"
                " WHERE watchlist_name = ? ORDER BY ticker",
                [name],
            ).fetchall()
            return [row[0] for row in result]
        except StorageError:
            raise
        except duckdb.Error as e:
            raise StorageError(f"Failed to get watchlist items: {e}") from e

    def watchlist_exists(self, name: str) -> bool:
        """Check if a watchlist exists."""
        try:
            result = self._conn.execute(
                "SELECT 1 FROM watchlists WHERE name = ?", [name]
            ).fetchone()
            return result is not None
        except duckdb.Error as e:
            raise StorageError(f"Failed to check watchlist: {e}") from e

    # -- Ticker metadata --------------------------------------------------

    def get_ticker_name(self, ticker: str) -> str | None:
        """Return the cached company name for a ticker, or None."""
        try:
            result = self._conn.execute(
                "SELECT name FROM ticker_metadata WHERE ticker = ?", [ticker]
            ).fetchone()
            return result[0] if result else None
        except duckdb.Error:
            return None

    def store_ticker_name(self, ticker: str, name: str) -> None:
        """Cache a company name for a ticker (upsert)."""
        try:
            self._conn.execute(
                "INSERT OR REPLACE INTO ticker_metadata (ticker, name) VALUES (?, ?)",
                [ticker, name],
            )
        except duckdb.Error:
            logger.debug("Failed to cache ticker name for %s", ticker, exc_info=True)

    # -- News -------------------------------------------------------------

    def store_news(self, items: list) -> int:
        """Store news items with INSERT OR IGNORE semantics.

        Returns count of new items.
        """
        if not items:
            return 0
        new_count = 0
        try:
            for item in items:
                result = self._conn.execute(
                    "SELECT 1 FROM news WHERE id = ?", [item.id]
                ).fetchone()
                if result is None:
                    self._conn.execute(
                        "INSERT INTO news"
                        " (id, source, feed, headline,"
                        " summary, url, published_at)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [
                            item.id,
                            item.source,
                            item.feed,
                            item.headline,
                            item.summary,
                            item.url,
                            item.published_at,
                        ],
                    )
                    new_count += 1
        except duckdb.Error as e:
            raise StorageError(f"Failed to store news: {e}") from e
        return new_count

    def get_news(self, limit: int = 50) -> list[dict]:
        """Return recent news items, most recent first."""
        try:
            result = self._conn.execute(
                "SELECT id, source, feed, headline,"
                " summary, url, published_at, fetched_at"
                " FROM news ORDER BY published_at DESC LIMIT ?",
                [limit],
            ).fetchall()
            return [
                {
                    "id": row[0],
                    "source": row[1],
                    "feed": row[2],
                    "headline": row[3],
                    "summary": row[4],
                    "url": row[5],
                    "published_at": row[6],
                    "fetched_at": row[7],
                }
                for row in result
            ]
        except duckdb.Error as e:
            raise StorageError(f"Failed to get news: {e}") from e

    def get_news_count(self) -> int:
        """Return total number of news items."""
        try:
            result = self._conn.execute("SELECT COUNT(*) FROM news").fetchone()
            return result[0] if result else 0
        except duckdb.Error as e:
            raise StorageError(f"Failed to get news count: {e}") from e

    def delete_old_news(self, retention_days: int = 7) -> int:
        """Delete news items older than retention_days.

        Returns count of deleted rows.
        """
        try:
            count_before = self.get_news_count()
            cutoff = datetime.now() - timedelta(days=retention_days)
            self._conn.execute(
                "DELETE FROM news WHERE fetched_at < ?",
                [cutoff],
            )
            count_after = self.get_news_count()
            return count_before - count_after
        except duckdb.Error as e:
            raise StorageError(f"Failed to delete old news: {e}") from e

    # -- Worker runs ------------------------------------------------------

    def store_worker_run(
        self,
        task_name: str,
        started_at: datetime,
        completed_at: datetime,
        status: str,
        message: str | None,
        items_processed: int,
    ) -> None:
        """Record a daemon task run."""
        try:
            self._conn.execute(
                "INSERT INTO worker_runs "
                "(task_name, started_at, completed_at, status, message, items_processed) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [task_name, started_at, completed_at, status, message, items_processed],
            )
        except duckdb.Error as e:
            raise StorageError(f"Failed to store worker run: {e}") from e

    def get_recent_worker_runs(self, limit: int = 10) -> list[dict]:
        """Return recent worker runs, most recent first."""
        try:
            result = self._conn.execute(
                "SELECT task_name, started_at, completed_at, status, message, items_processed "
                "FROM worker_runs ORDER BY started_at DESC LIMIT ?",
                [limit],
            ).fetchall()
            return [
                {
                    "task_name": row[0],
                    "started_at": row[1],
                    "completed_at": row[2],
                    "status": row[3],
                    "message": row[4],
                    "items_processed": row[5],
                }
                for row in result
            ]
        except duckdb.Error as e:
            raise StorageError(f"Failed to get worker runs: {e}") from e

    def get_last_worker_run(self, task_name: str) -> dict | None:
        """Return the most recent run for a specific task."""
        try:
            result = self._conn.execute(
                "SELECT task_name, started_at, completed_at, status, message, items_processed "
                "FROM worker_runs WHERE task_name = ? ORDER BY started_at DESC LIMIT 1",
                [task_name],
            ).fetchone()
            if result is None:
                return None
            return {
                "task_name": result[0],
                "started_at": result[1],
                "completed_at": result[2],
                "status": result[3],
                "message": result[4],
                "items_processed": result[5],
            }
        except duckdb.Error as e:
            raise StorageError(f"Failed to get last worker run: {e}") from e

    # -- lifecycle --------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

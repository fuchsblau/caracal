"""DuckDB storage implementation."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import TracebackType

import duckdb
import pandas as pd

from caracal.providers.types import StorageError


class DuckDBStorage:
    """DuckDB-based storage for OHLCV and indicator data."""

    def __init__(self, db_path: str = "~/.caracal/caracal.db") -> None:
        try:
            if db_path != ":memory:":
                resolved = Path(db_path).expanduser()
                resolved.parent.mkdir(parents=True, exist_ok=True)
                db_path = str(resolved)
            self._conn = duckdb.connect(db_path)
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
        """Create tables if they do not exist."""
        try:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv (
                    ticker VARCHAR NOT NULL,
                    date DATE NOT NULL,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume BIGINT,
                    PRIMARY KEY (ticker, date)
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS indicators (
                    ticker VARCHAR NOT NULL,
                    date DATE NOT NULL,
                    name VARCHAR NOT NULL,
                    value DOUBLE,
                    PRIMARY KEY (ticker, date, name)
                )
            """)
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

    # -- lifecycle --------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

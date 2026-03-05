from datetime import date

import pandas as pd

from caracal.storage.duckdb import DuckDBStorage


class TestStoreAndGetOHLCV:
    def test_store_and_retrieve(self, storage):
        df = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 2)],
                "open": [100.0, 101.0],
                "high": [105.0, 106.0],
                "low": [99.0, 100.0],
                "close": [104.0, 105.0],
                "volume": [1000, 1100],
            }
        )
        count = storage.store_ohlcv("AAPL", df)
        assert count == 2

        result = storage.get_ohlcv("AAPL")
        assert len(result) == 2
        assert list(result.columns) == [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

    def test_get_empty_ticker(self, storage):
        result = storage.get_ohlcv("UNKNOWN")
        assert len(result) == 0

    def test_upsert_no_duplicates(self, storage):
        df1 = pd.DataFrame(
            {
                "date": [date(2024, 1, 1)],
                "open": [100.0],
                "high": [105.0],
                "low": [99.0],
                "close": [104.0],
                "volume": [1000],
            }
        )
        df2 = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 2)],
                "open": [100.0, 101.0],
                "high": [105.0, 106.0],
                "low": [99.0, 100.0],
                "close": [104.0, 105.0],
                "volume": [1000, 1100],
            }
        )
        storage.store_ohlcv("AAPL", df1)
        storage.store_ohlcv("AAPL", df2)
        result = storage.get_ohlcv("AAPL")
        assert len(result) == 2

    def test_date_range_filter(self, storage):
        df = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)],
                "open": [100.0, 101.0, 102.0],
                "high": [105.0, 106.0, 107.0],
                "low": [99.0, 100.0, 101.0],
                "close": [104.0, 105.0, 106.0],
                "volume": [1000, 1100, 1200],
            }
        )
        storage.store_ohlcv("AAPL", df)
        result = storage.get_ohlcv("AAPL", start_date=date(2024, 1, 2))
        assert len(result) == 2

    def test_end_date_filter(self, storage):
        """get_ohlcv should filter by end_date."""
        df = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)],
                "open": [100.0, 101.0, 102.0],
                "high": [105.0, 106.0, 107.0],
                "low": [99.0, 100.0, 101.0],
                "close": [104.0, 105.0, 106.0],
                "volume": [1000, 2000, 3000],
            }
        )
        storage.store_ohlcv("TEST", df)
        result = storage.get_ohlcv("TEST", end_date=date(2024, 1, 2))
        assert len(result) == 2

    def test_start_and_end_date_filter(self, storage):
        """get_ohlcv should filter by both start_date and end_date."""
        df = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)],
                "open": [100.0, 101.0, 102.0],
                "high": [105.0, 106.0, 107.0],
                "low": [99.0, 100.0, 101.0],
                "close": [104.0, 105.0, 106.0],
                "volume": [1000, 2000, 3000],
            }
        )
        storage.store_ohlcv("TEST", df)
        result = storage.get_ohlcv(
            "TEST", start_date=date(2024, 1, 2), end_date=date(2024, 1, 2)
        )
        assert len(result) == 1

    def test_store_empty_dataframe(self, storage):
        """Storing empty DataFrame should return 0 and not error."""
        df = pd.DataFrame(
            columns=["date", "open", "high", "low", "close", "volume"]
        )
        assert storage.store_ohlcv("TEST", df) == 0


class TestDeltaFetch:
    def test_latest_date(self, storage):
        df = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 2)],
                "open": [100.0, 101.0],
                "high": [105.0, 106.0],
                "low": [99.0, 100.0],
                "close": [104.0, 105.0],
                "volume": [1000, 1100],
            }
        )
        storage.store_ohlcv("AAPL", df)
        assert storage.get_latest_date("AAPL") == date(2024, 1, 2)

    def test_latest_date_empty(self, storage):
        assert storage.get_latest_date("UNKNOWN") is None


class TestIndicators:
    def test_store_and_get_indicators(self, storage):
        df = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 2)],
                "name": ["sma_20", "sma_20"],
                "value": [100.5, 101.0],
            }
        )
        count = storage.store_indicators("AAPL", df)
        assert count == 2

        result = storage.get_indicators("AAPL")
        assert len(result) == 2

    def test_get_indicators_by_name(self, storage):
        df = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 1)],
                "name": ["sma_20", "rsi_14"],
                "value": [100.5, 55.0],
            }
        )
        storage.store_indicators("AAPL", df)
        result = storage.get_indicators("AAPL", names=["rsi_14"])
        assert len(result) == 1
        assert result.iloc[0]["name"] == "rsi_14"

    def test_store_empty_indicators(self, storage):
        """Storing empty indicator DataFrame should return 0."""
        df = pd.DataFrame(columns=["date", "name", "value"])
        assert storage.store_indicators("TEST", df) == 0


class TestContextManager:
    def test_context_manager_protocol(self, tmp_path):
        """Storage should work as context manager."""
        db_path = str(tmp_path / "test.db")
        with DuckDBStorage(db_path) as s:
            s.create_watchlist("test")
        # Connection should be closed after exit - re-opening should work
        with DuckDBStorage(db_path) as s:
            assert s.watchlist_exists("test")

    def test_file_based_storage_creates_parent_dirs(self, tmp_path):
        """Storage should create parent directories for db_path."""
        db_path = str(tmp_path / "sub" / "dir" / "test.db")
        storage = DuckDBStorage(db_path)
        storage.create_watchlist("test")
        storage.close()

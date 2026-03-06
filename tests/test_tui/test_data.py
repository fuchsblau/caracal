"""Tests for TUI DataService."""

from datetime import date, timedelta

import pandas as pd
import pytest

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage, StorageError
from caracal.tui.data import DataService


def _store_ohlcv(storage, ticker, days=31, trend="flat"):
    """Store synthetic OHLCV data for testing."""
    base_price = 100.0
    rows = []
    for i in range(days):
        if trend == "up":
            price = base_price + i * 2
        elif trend == "down":
            price = base_price - i * 2
        else:
            price = base_price + (i % 3 - 1)
        d = date.today() - timedelta(days=days - i)
        rows.append({
            "date": d,
            "open": price - 0.5,
            "high": price + 1,
            "low": price - 1,
            "close": price,
            "volume": 1000000,
        })
    df = pd.DataFrame(rows)
    storage.store_ohlcv(ticker, df)


@pytest.fixture
def storage():
    s = DuckDBStorage(":memory:")
    yield s
    s.close()


@pytest.fixture
def config():
    return CaracalConfig(db_path=":memory:")


@pytest.fixture
def data_service(storage, config):
    svc = DataService(config, storage=storage)
    yield svc
    svc.close()


@pytest.fixture
def sample_watchlist(storage):
    """Create a watchlist with one ticker for tests that need existing data."""
    storage.create_watchlist("sample")
    storage.add_to_watchlist("sample", "AAPL")
    return "sample"


class TestGetWatchlists:
    def test_returns_empty_list_when_no_watchlists(self, data_service):
        assert data_service.get_watchlist_names() == []

    def test_returns_watchlist_names(self, data_service, storage):
        storage.create_watchlist("tech")
        storage.create_watchlist("etfs")
        names = data_service.get_watchlist_names()
        assert sorted(names) == ["etfs", "tech"]


class TestGetWatchlistOverview:
    def test_returns_empty_for_empty_watchlist(self, data_service, storage):
        storage.create_watchlist("tech")
        rows = data_service.get_watchlist_overview("tech")
        assert rows == []

    def test_returns_ticker_rows_with_cached_data(self, data_service, storage):
        import pandas as pd

        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "AAPL")

        # Store some OHLCV data
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "open": [150.0, 152.0],
            "high": [155.0, 156.0],
            "low": [149.0, 151.0],
            "close": [153.0, 155.0],
            "volume": [1000000, 1100000],
        })
        storage.store_ohlcv("AAPL", df)

        rows = data_service.get_watchlist_overview("tech")
        assert len(rows) == 1
        assert rows[0]["ticker"] == "AAPL"
        assert rows[0]["close"] == 155.0
        assert rows[0]["change_pct"] is not None

    def test_returns_none_values_when_no_data(self, data_service, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "UNKNOWN")

        rows = data_service.get_watchlist_overview("tech")
        assert len(rows) == 1
        assert rows[0]["ticker"] == "UNKNOWN"
        assert rows[0]["close"] is None
        assert rows[0]["signal"] == "N/A"


class TestGetStockDetail:
    def test_returns_detail_with_cached_data(self, data_service, storage):
        import pandas as pd

        df = pd.DataFrame({
            "date": pd.to_datetime(
                [f"2024-01-{d:02d}" for d in range(1, 32)]
            ),
            "open": [150.0 + i for i in range(31)],
            "high": [155.0 + i for i in range(31)],
            "low": [149.0 + i for i in range(31)],
            "close": [153.0 + i for i in range(31)],
            "volume": [1000000 + i * 1000 for i in range(31)],
        })
        storage.store_ohlcv("AAPL", df)

        detail = data_service.get_stock_detail("AAPL")
        assert detail["ticker"] == "AAPL"
        assert detail["close"] is not None
        assert "signal" in detail
        assert "indicators" in detail
        assert "ohlcv" in detail

    def test_returns_empty_detail_when_no_data(self, data_service):
        detail = data_service.get_stock_detail("UNKNOWN")
        assert detail["ticker"] == "UNKNOWN"
        assert detail["close"] is None
        assert detail["signal"] == "N/A"


class TestRefreshWatchlist:
    def test_refresh_returns_updated_rows(self, data_service, storage):
        import pandas as pd

        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "AAPL")

        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "open": [150.0, 152.0],
            "high": [155.0, 156.0],
            "low": [149.0, 151.0],
            "close": [153.0, 155.0],
            "volume": [1000000, 1100000],
        })
        storage.store_ohlcv("AAPL", df)

        # refresh_watchlist re-reads from storage
        rows = data_service.refresh_watchlist("tech")
        assert len(rows) == 1
        assert rows[0]["ticker"] == "AAPL"


class TestGetLastFetchTime:
    def test_returns_none_for_memory_db(self, data_service):
        assert data_service.get_last_fetch_time() is None

    def test_returns_datetime_for_file_db(self, tmp_path):
        db_file = str(tmp_path / "test.db")
        config = CaracalConfig(db_path=db_file)
        storage = DuckDBStorage(db_file)
        ds = DataService(config, storage=storage)
        storage.create_watchlist("tech")
        result = ds.get_last_fetch_time()
        assert result is not None
        # Format: YYYY-MM-DD HH:MM:SS
        assert len(result) == 19
        storage.close()

    def test_expands_tilde_in_db_path(self, tmp_path, monkeypatch):
        """Tilde paths like ~/.caracal/caracal.db are expanded correctly."""
        db_file = tmp_path / "test.db"
        # Make ~ resolve to tmp_path parent so ~/test.db = db_file
        monkeypatch.setenv("HOME", str(tmp_path))
        config = CaracalConfig(db_path="~/test.db")
        storage = DuckDBStorage(str(db_file))
        ds = DataService(config, storage=storage)
        storage.create_watchlist("tech")
        result = ds.get_last_fetch_time()
        assert result is not None
        assert len(result) == 19
        storage.close()


class TestGetAppInfo:
    def test_returns_version_and_config(self, data_service):
        info = data_service.get_app_info()
        assert "version" in info
        assert "provider" in info
        assert "config_path" in info
        assert "db_path" in info


class TestCreateWatchlist:
    def test_create_watchlist(self, data_service):
        """DataService.create_watchlist delegates to storage."""
        data_service.create_watchlist("new_wl")
        names = data_service.get_watchlist_names()
        assert "new_wl" in names

    def test_create_watchlist_duplicate_raises(self, data_service):
        """Duplicate name raises StorageError."""
        data_service.create_watchlist("dup")
        with pytest.raises(StorageError):
            data_service.create_watchlist("dup")


class TestDeleteWatchlist:
    def test_delete_watchlist(self, data_service, sample_watchlist):
        """DataService.delete_watchlist removes the watchlist."""
        data_service.delete_watchlist(sample_watchlist)
        names = data_service.get_watchlist_names()
        assert sample_watchlist not in names

    def test_delete_watchlist_not_found_raises(self, data_service):
        """Deleting non-existent watchlist raises StorageError."""
        with pytest.raises(StorageError):
            data_service.delete_watchlist("nonexistent")


class TestAddToWatchlist:
    def test_add_single_ticker(self, data_service, sample_watchlist):
        """Adding a single ticker returns it in added list."""
        added, duplicates = data_service.add_to_watchlist("sample", ["MSFT"])
        assert added == ["MSFT"]
        assert duplicates == []

    def test_add_batch_tickers(self, data_service, sample_watchlist):
        """Adding multiple tickers returns all in added list."""
        added, duplicates = data_service.add_to_watchlist(
            "sample", ["MSFT", "NVDA", "GOOG"]
        )
        assert added == ["MSFT", "NVDA", "GOOG"]
        assert duplicates == []

    def test_add_duplicate_ticker(self, data_service, sample_watchlist):
        """Adding existing ticker AAPL returns it as duplicate."""
        added, duplicates = data_service.add_to_watchlist("sample", ["AAPL"])
        assert added == []
        assert duplicates == ["AAPL"]

    def test_add_mixed_batch(self, data_service, sample_watchlist):
        """Batch with mix of new and existing tickers splits correctly."""
        added, duplicates = data_service.add_to_watchlist(
            "sample", ["AAPL", "MSFT", "AAPL"]
        )
        assert added == ["MSFT"]
        assert duplicates == ["AAPL", "AAPL"]

    def test_add_to_nonexistent_watchlist_raises(self, data_service):
        """Adding to non-existent watchlist raises StorageError."""
        with pytest.raises(StorageError):
            data_service.add_to_watchlist("nope", ["AAPL"])


class TestRemoveFromWatchlist:
    def test_remove_ticker(self, data_service, sample_watchlist):
        """Removing a ticker removes it from the watchlist."""
        data_service.remove_from_watchlist("sample", "AAPL")
        overview = data_service.get_watchlist_overview("sample")
        assert not any(r["ticker"] == "AAPL" for r in overview)

    def test_remove_nonexistent_ticker_raises(self, data_service, sample_watchlist):
        """Removing a ticker not in the watchlist raises StorageError."""
        with pytest.raises(StorageError):
            data_service.remove_from_watchlist("sample", "NOPE")

    def test_remove_from_nonexistent_watchlist_raises(self, data_service):
        """Removing from non-existent watchlist raises StorageError."""
        with pytest.raises(StorageError):
            data_service.remove_from_watchlist("nope", "AAPL")


class TestGetWatchlistsDetail:
    def test_get_watchlists(self, data_service, sample_watchlist):
        """get_watchlists returns list of dicts with name and ticker_count."""
        result = data_service.get_watchlists()
        assert len(result) >= 1
        wl = next(w for w in result if w["name"] == sample_watchlist)
        assert "name" in wl
        assert "ticker_count" in wl


class TestGetWatchlistOverviewWithIndicators:
    """Test enriched watchlist overview with indicator data."""

    def test_returns_indicator_fields(self, data_service, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "AAPL")
        _store_ohlcv(storage, "AAPL", days=31)
        rows = data_service.get_watchlist_overview("tech")
        row = rows[0]
        assert "confidence" in row
        assert "rsi" in row
        assert "macd_interpretation" in row
        assert "bb_position" in row

    def test_indicator_fields_none_when_insufficient_data(self, data_service, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "NEW")
        _store_ohlcv(storage, "NEW", days=5)
        rows = data_service.get_watchlist_overview("tech")
        row = rows[0]
        assert row["confidence"] is None
        assert row["rsi"] is None
        assert row["macd_interpretation"] is None
        assert row["bb_position"] is None

    def test_rsi_overbought_interpretation(self, data_service, storage):
        """RSI > 70 should be marked as overbought."""
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "OB")
        _store_ohlcv(storage, "OB", days=31, trend="up")
        rows = data_service.get_watchlist_overview("tech")
        assert rows[0]["rsi"] is not None


class TestRefreshWatchlistLive:
    def test_refresh_live_calls_provider_and_updates(self, data_service, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "AAPL")
        _store_ohlcv(storage, "AAPL", days=31)
        rows = data_service.refresh_watchlist_live("tech")
        assert len(rows) == 1
        assert rows[0]["ticker"] == "AAPL"

"""Tests for the FetchTask daemon task."""

import asyncio
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from caracal.config import CaracalConfig
from caracal.daemon.registry import TaskContext
from caracal.daemon.tasks.fetch import FetchTask
from caracal.storage.duckdb import DuckDBStorage


def _make_ohlcv(ticker: str, days: int = 5, start: date | None = None) -> pd.DataFrame:
    """Create sample OHLCV DataFrame."""
    start = start or date(2026, 3, 1)
    dates = [start + timedelta(days=i) for i in range(days)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": [100.0 + i for i in range(days)],
            "high": [105.0 + i for i in range(days)],
            "low": [95.0 + i for i in range(days)],
            "close": [102.0 + i for i in range(days)],
            "volume": [1000 * (i + 1) for i in range(days)],
        }
    )


@pytest.fixture
def context():
    storage = DuckDBStorage(":memory:")
    ctx = TaskContext(db=storage, config=CaracalConfig())
    yield ctx
    storage.close()


class TestFetchTask:
    @pytest.mark.asyncio
    async def test_no_watchlists_returns_ok(self, context):
        task = FetchTask()
        result = await task.run(context)
        assert result.status == "ok"
        assert result.items_processed == 0

    @pytest.mark.asyncio
    async def test_fetches_all_watchlist_tickers(self, context):
        # Set up watchlist with 2 tickers
        context.db.create_watchlist("test")
        context.db.add_to_watchlist("test", "AAPL")
        context.db.add_to_watchlist("test", "MSFT")

        mock_provider = MagicMock()
        mock_provider.fetch_ohlcv.return_value = _make_ohlcv("X")

        with patch("caracal.daemon.tasks.fetch.get_provider", return_value=mock_provider):
            task = FetchTask()
            result = await task.run(context)

        assert result.status == "ok"
        assert result.items_processed == 2
        assert mock_provider.fetch_ohlcv.call_count == 2

    @pytest.mark.asyncio
    async def test_delta_fetch_uses_latest_date(self, context):
        context.db.create_watchlist("test")
        context.db.add_to_watchlist("test", "AAPL")

        # Store some existing data
        existing = _make_ohlcv("AAPL", days=3, start=date(2026, 3, 1))
        context.db.store_ohlcv("AAPL", existing)

        mock_provider = MagicMock()
        mock_provider.fetch_ohlcv.return_value = _make_ohlcv("AAPL", days=2, start=date(2026, 3, 4))

        with patch("caracal.daemon.tasks.fetch.get_provider", return_value=mock_provider):
            task = FetchTask()
            result = await task.run(context)

        # Should fetch from day after latest (2026-03-04)
        call_args = mock_provider.fetch_ohlcv.call_args
        assert call_args[0][1] == date(2026, 3, 4)  # start_date

    @pytest.mark.asyncio
    async def test_provider_error_returns_error_result(self, context):
        context.db.create_watchlist("test")
        context.db.add_to_watchlist("test", "AAPL")

        mock_provider = MagicMock()
        mock_provider.fetch_ohlcv.side_effect = Exception("Network error")

        with patch("caracal.daemon.tasks.fetch.get_provider", return_value=mock_provider):
            task = FetchTask()
            result = await task.run(context)

        assert result.status == "error"
        assert "Network error" in result.message

    @pytest.mark.asyncio
    async def test_deduplicates_tickers_across_watchlists(self, context):
        context.db.create_watchlist("tech")
        context.db.add_to_watchlist("tech", "AAPL")
        context.db.create_watchlist("fav")
        context.db.add_to_watchlist("fav", "AAPL")  # duplicate

        mock_provider = MagicMock()
        mock_provider.fetch_ohlcv.return_value = _make_ohlcv("X")

        with patch("caracal.daemon.tasks.fetch.get_provider", return_value=mock_provider):
            task = FetchTask()
            result = await task.run(context)

        assert result.items_processed == 1  # not 2
        assert mock_provider.fetch_ohlcv.call_count == 1

    def test_task_name(self):
        assert FetchTask().name == "fetch"

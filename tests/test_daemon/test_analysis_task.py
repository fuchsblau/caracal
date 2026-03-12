"""Tests for the AnalysisTask daemon task."""

from datetime import date, timedelta

import pandas as pd
import pytest

from caracal.config import CaracalConfig
from caracal.daemon.registry import TaskContext
from caracal.daemon.tasks.analysis import AnalysisTask
from caracal.storage.duckdb import DuckDBStorage


def _make_ohlcv(days: int = 250) -> pd.DataFrame:
    """Create sample OHLCV with enough data for all indicators."""
    start = date(2025, 1, 1)
    dates = [start + timedelta(days=i) for i in range(days)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": [100.0 + i * 0.1 for i in range(days)],
            "high": [105.0 + i * 0.1 for i in range(days)],
            "low": [95.0 + i * 0.1 for i in range(days)],
            "close": [102.0 + i * 0.1 for i in range(days)],
            "volume": [1000 * (i + 1) for i in range(days)],
        }
    )


@pytest.fixture
def context():
    storage = DuckDBStorage(":memory:")
    ctx = TaskContext(db=storage, config=CaracalConfig())
    yield ctx
    storage.close()


class TestAnalysisTask:
    @pytest.mark.asyncio
    async def test_no_watchlists_returns_ok(self, context):
        task = AnalysisTask()
        result = await task.run(context)
        assert result.status == "ok"
        assert result.items_processed == 0

    @pytest.mark.asyncio
    async def test_analyzes_ticker_with_data(self, context):
        context.db.create_watchlist("test")
        context.db.add_to_watchlist("test", "AAPL")
        context.db.store_ohlcv("AAPL", _make_ohlcv())

        task = AnalysisTask()
        result = await task.run(context)

        assert result.status == "ok"
        assert result.items_processed == 1

        # Verify indicators were stored
        indicators = context.db.get_indicators("AAPL")
        assert not indicators.empty
        names = indicators["name"].unique()
        assert "sma_20" in names
        assert "rsi_14" in names

    @pytest.mark.asyncio
    async def test_skips_ticker_without_data(self, context):
        context.db.create_watchlist("test")
        context.db.add_to_watchlist("test", "AAPL")
        # No OHLCV data stored

        task = AnalysisTask()
        result = await task.run(context)

        assert result.status == "ok"
        assert result.items_processed == 0

    @pytest.mark.asyncio
    async def test_deduplicates_tickers(self, context):
        context.db.create_watchlist("a")
        context.db.add_to_watchlist("a", "AAPL")
        context.db.create_watchlist("b")
        context.db.add_to_watchlist("b", "AAPL")
        context.db.store_ohlcv("AAPL", _make_ohlcv())

        task = AnalysisTask()
        result = await task.run(context)

        assert result.items_processed == 1

    def test_task_name(self):
        assert AnalysisTask().name == "analysis"

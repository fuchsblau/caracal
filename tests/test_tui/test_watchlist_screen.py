"""Tests for WatchlistScreen."""

import pytest

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui import CaracalApp
from caracal.tui.data import DataService


@pytest.fixture
def storage():
    s = DuckDBStorage(":memory:")
    yield s
    s.close()


@pytest.fixture
def config():
    return CaracalConfig(db_path=":memory:")


@pytest.fixture
def app_with_data(config, storage):
    """App with a watchlist containing one ticker with data."""
    import pandas as pd

    storage.create_watchlist("tech")
    storage.add_to_watchlist("tech", "AAPL")
    storage.add_to_watchlist("tech", "MSFT")

    for ticker, base in [("AAPL", 150.0), ("MSFT", 350.0)]:
        df = pd.DataFrame({
            "date": pd.to_datetime([f"2024-01-{d:02d}" for d in range(1, 32)]),
            "open": [base + i for i in range(31)],
            "high": [base + 5 + i for i in range(31)],
            "low": [base - 1 + i for i in range(31)],
            "close": [base + 3 + i for i in range(31)],
            "volume": [1000000 + i * 1000 for i in range(31)],
        })
        storage.store_ohlcv(ticker, df)

    data_service = DataService(config, storage=storage)
    app = CaracalApp(config=config, data_service=data_service)
    return app


class TestWatchlistScreen:
    @pytest.mark.asyncio
    async def test_shows_watchlist_data(self, app_with_data):
        async with app_with_data.run_test():
            # The DataTable should show tickers
            from textual.widgets import DataTable
            table = app_with_data.screen.query_one(DataTable)
            assert table.row_count == 2

    @pytest.mark.asyncio
    async def test_shows_empty_watchlist_message(self, config):
        storage = DuckDBStorage(":memory:")
        storage.create_watchlist("empty")
        data_service = DataService(config, storage=storage)
        app = CaracalApp(config=config, data_service=data_service)

        async with app.run_test():
            # Should show hint text, not crash
            assert app.screen is not None

    @pytest.mark.asyncio
    async def test_shows_no_watchlist_message(self, config):
        storage = DuckDBStorage(":memory:")
        data_service = DataService(config, storage=storage)
        app = CaracalApp(config=config, data_service=data_service)

        async with app.run_test():
            assert app.screen is not None

    @pytest.mark.asyncio
    async def test_quit_with_q(self, app_with_data):
        async with app_with_data.run_test() as pilot:
            await pilot.press("q")

"""Tests for StockDetailScreen."""

import pandas as pd
import pytest
from rich.text import Text

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui import CaracalApp
from caracal.tui.data import DataService


@pytest.fixture
def storage_with_data():
    s = DuckDBStorage(":memory:")
    s.create_watchlist("tech")
    s.add_to_watchlist("tech", "AAPL")

    df = pd.DataFrame({
        "date": pd.to_datetime([f"2024-01-{d:02d}" for d in range(1, 32)]),
        "open": [150.0 + i for i in range(31)],
        "high": [155.0 + i for i in range(31)],
        "low": [149.0 + i for i in range(31)],
        "close": [153.0 + i for i in range(31)],
        "volume": [1000000 + i * 1000 for i in range(31)],
    })
    s.store_ohlcv("AAPL", df)
    yield s
    s.close()


@pytest.fixture
def app(storage_with_data):
    config = CaracalConfig(db_path=":memory:")
    data_service = DataService(config, storage=storage_with_data)
    return CaracalApp(config=config, data_service=data_service)


class TestStockDetailScreen:
    @pytest.mark.asyncio
    async def test_navigate_to_detail_and_back(self, app):
        async with app.run_test() as pilot:
            # Trigger select_row action to open detail screen
            app.screen.action_select_row()
            await pilot.pause()
            from caracal.tui.screens.stock_detail import StockDetailScreen
            assert isinstance(app.screen, StockDetailScreen)

            # Press escape to go back
            await pilot.press("escape")
            from caracal.tui.screens.watchlist import WatchlistScreen
            assert isinstance(app.screen, WatchlistScreen)

    @pytest.mark.asyncio
    async def test_detail_shows_ticker_name(self, app):
        async with app.run_test() as pilot:
            app.screen.action_select_row()
            await pilot.pause()
            assert "AAPL" in app.screen.sub_title


class TestRichTextStyling:
    @pytest.mark.asyncio
    async def test_indicator_value_is_rich_text_right_aligned(self, app):
        async with app.run_test() as pilot:
            app.screen.action_select_row()
            await pilot.pause()
            screen = app.screen
            table = screen.query_one("#indicators-table")
            if table.row_count > 0:
                from textual.widgets._data_table import Coordinate
                cell = table.get_cell_at(Coordinate(0, 1))
                assert isinstance(cell, Text)
                assert cell.justify == "right"

    @pytest.mark.asyncio
    async def test_ohlcv_close_is_rich_text_right_aligned(self, app):
        async with app.run_test() as pilot:
            app.screen.action_select_row()
            await pilot.pause()
            screen = app.screen
            table = screen.query_one("#ohlcv-table")
            if table.row_count > 0:
                from textual.widgets._data_table import Coordinate
                cell = table.get_cell_at(Coordinate(0, 4))  # Close column
                assert isinstance(cell, Text)
                assert cell.justify == "right"

    @pytest.mark.asyncio
    async def test_ohlcv_volume_is_right_aligned(self, app):
        async with app.run_test() as pilot:
            app.screen.action_select_row()
            await pilot.pause()
            screen = app.screen
            table = screen.query_one("#ohlcv-table")
            if table.row_count > 0:
                from textual.widgets._data_table import Coordinate
                cell = table.get_cell_at(Coordinate(0, 5))  # Volume column
                assert isinstance(cell, Text)
                assert cell.justify == "right"

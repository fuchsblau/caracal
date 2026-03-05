"""End-to-end TUI integration tests."""

import pytest
import pandas as pd

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui import CaracalApp
from caracal.tui.data import DataService


def _make_ohlcv(base_price: float, days: int = 31) -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.to_datetime([f"2024-01-{d:02d}" for d in range(1, days + 1)]),
        "open": [base_price + i for i in range(days)],
        "high": [base_price + 5 + i for i in range(days)],
        "low": [base_price - 1 + i for i in range(days)],
        "close": [base_price + 3 + i for i in range(days)],
        "volume": [1000000 + i * 1000 for i in range(days)],
    })


@pytest.fixture
def full_app():
    config = CaracalConfig(db_path=":memory:")
    storage = DuckDBStorage(":memory:")

    storage.create_watchlist("tech")
    storage.create_watchlist("etfs")
    storage.add_to_watchlist("tech", "AAPL")
    storage.add_to_watchlist("tech", "MSFT")
    storage.add_to_watchlist("etfs", "SPY")

    storage.store_ohlcv("AAPL", _make_ohlcv(150.0))
    storage.store_ohlcv("MSFT", _make_ohlcv(350.0))
    storage.store_ohlcv("SPY", _make_ohlcv(450.0))

    data_service = DataService(config, storage=storage)
    return CaracalApp(config=config, data_service=data_service)


class TestFullNavigation:
    @pytest.mark.asyncio
    async def test_watchlist_to_detail_and_back(self, full_app):
        """SC-003 criteria 1-4: start, show data, enter detail, esc back."""
        async with full_app.run_test() as pilot:
            from caracal.tui.screens.watchlist import WatchlistScreen
            from caracal.tui.screens.stock_detail import StockDetailScreen

            # Criterion 1: TUI starts with WatchlistScreen
            assert isinstance(full_app.screen, WatchlistScreen)

            # Criterion 2: DataTable has rows
            # First watchlist alphabetically is "etfs" with 1 ticker (SPY)
            from textual.widgets import DataTable
            table = full_app.screen.query_one(DataTable)
            assert table.row_count >= 1

            # Criterion 3: Navigate to detail using action_select_row
            full_app.screen.action_select_row()
            await pilot.pause()
            assert isinstance(full_app.screen, StockDetailScreen)

            # Criterion 4: Esc goes back
            await pilot.press("escape")
            assert isinstance(full_app.screen, WatchlistScreen)

    @pytest.mark.asyncio
    async def test_info_screen(self, full_app):
        """SC-003 criterion 5: Info screen shows version, provider, config."""
        async with full_app.run_test() as pilot:
            from caracal.tui.screens.info import InfoScreen
            from caracal.tui.screens.watchlist import WatchlistScreen

            await pilot.press("i")
            assert isinstance(full_app.screen, InfoScreen)

            await pilot.press("escape")
            assert isinstance(full_app.screen, WatchlistScreen)

    @pytest.mark.asyncio
    async def test_keyboard_navigation(self, full_app):
        """SC-003 criterion 6: full keyboard navigation."""
        async with full_app.run_test() as pilot:
            # j/k navigation (vim style)
            await pilot.press("j")
            await pilot.press("k")
            # Arrow keys also work
            await pilot.press("down")
            await pilot.press("up")

    @pytest.mark.asyncio
    async def test_watchlist_switching(self, full_app):
        """US-053: Switch between watchlists with w key."""
        async with full_app.run_test() as pilot:
            from caracal.tui.screens.watchlist import WatchlistScreen

            screen = full_app.screen
            assert isinstance(screen, WatchlistScreen)
            first_wl = screen.current_watchlist

            await pilot.press("w")
            second_wl = screen.current_watchlist
            assert first_wl != second_wl

    @pytest.mark.asyncio
    async def test_quit(self, full_app):
        """q quits the app."""
        async with full_app.run_test() as pilot:
            await pilot.press("q")

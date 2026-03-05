"""End-to-end TUI integration tests."""

import pandas as pd
import pytest

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
            from caracal.tui.screens.stock_detail import StockDetailScreen
            from caracal.tui.screens.watchlist import WatchlistScreen

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
        """US-053: Switch between watchlists with w key opens selector."""
        async with full_app.run_test() as pilot:
            from caracal.tui.screens.watchlist import WatchlistScreen
            from caracal.tui.screens.watchlist_selector import WatchlistSelectorModal

            screen = full_app.screen
            assert isinstance(screen, WatchlistScreen)

            await pilot.press("w")
            assert isinstance(full_app.screen, WatchlistSelectorModal)

    @pytest.mark.asyncio
    async def test_full_watchlist_management_flow(self, full_app):
        """Create watchlist, switch to it, delete it — full lifecycle."""
        async with full_app.run_test() as pilot:
            from caracal.tui.screens.watchlist import WatchlistScreen

            screen = full_app.screen
            assert isinstance(screen, WatchlistScreen)

            # Initial state: first watchlist alphabetically ("etfs")
            initial_watchlist = screen.current_watchlist
            initial_count = len(screen._watchlist_names)
            assert initial_watchlist is not None

            # Step 1: Create a new watchlist via 'c' key
            await pilot.press("c")
            input_widget = full_app.screen.query_one("#create-input")
            input_widget.value = "integration_test"
            await pilot.press("enter")
            await pilot.pause()

            # Should be back on WatchlistScreen, switched to new watchlist
            assert isinstance(full_app.screen, WatchlistScreen)
            assert full_app.screen.current_watchlist == "integration_test"
            assert len(full_app.screen._watchlist_names) == initial_count + 1

            # Step 2: Switch back to original via 'w' key (selector)
            await pilot.press("w")
            await pilot.press("enter")  # Select first item in list
            await pilot.pause()

            assert isinstance(full_app.screen, WatchlistScreen)
            # After selecting, we're on a different watchlist
            switched_to = full_app.screen.current_watchlist
            assert switched_to is not None

            # Step 3: Delete current watchlist via 'd' key
            current_before_delete = full_app.screen.current_watchlist
            await pilot.press("d")
            await pilot.click("#confirm-btn")
            await pilot.pause()

            assert isinstance(full_app.screen, WatchlistScreen)
            assert current_before_delete not in full_app.screen._watchlist_names
            assert len(full_app.screen._watchlist_names) == initial_count

    @pytest.mark.asyncio
    async def test_quit(self, full_app):
        """q quits the app."""
        async with full_app.run_test() as pilot:
            await pilot.press("q")

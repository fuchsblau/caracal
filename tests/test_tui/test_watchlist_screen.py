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


@pytest.fixture
def app_with_two_watchlists(config, storage):
    """App with two watchlists for testing switching/deletion."""
    import pandas as pd

    storage.create_watchlist("alpha")
    storage.create_watchlist("beta")
    storage.add_to_watchlist("alpha", "AAPL")
    storage.add_to_watchlist("beta", "TSLA")
    for ticker, base in [("AAPL", 150.0), ("TSLA", 250.0)]:
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
    return CaracalApp(config=config, data_service=data_service)


@pytest.fixture
def app_no_watchlists(config):
    """App with no watchlists."""
    storage = DuckDBStorage(":memory:")
    data_service = DataService(config, storage=storage)
    return CaracalApp(config=config, data_service=data_service)


@pytest.fixture
def app_empty_watchlist(config):
    """App with a watchlist that has no tickers."""
    storage = DuckDBStorage(":memory:")
    storage.create_watchlist("empty")
    data_service = DataService(config, storage=storage)
    return CaracalApp(config=config, data_service=data_service)


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


class TestWatchlistManagement:
    @pytest.mark.asyncio
    async def test_create_watchlist_opens_modal(self, app_with_data):
        async with app_with_data.run_test() as pilot:
            await pilot.press("c")
            from caracal.tui.screens.create_watchlist import CreateWatchlistModal

            assert isinstance(app_with_data.screen, CreateWatchlistModal)

    @pytest.mark.asyncio
    async def test_create_watchlist_flow(self, app_with_data):
        async with app_with_data.run_test() as pilot:
            await pilot.press("c")
            input_widget = app_with_data.screen.query_one("#create-input")
            input_widget.value = "new_wl"
            await pilot.press("enter")
            await pilot.pause()
            from caracal.tui.screens.watchlist import WatchlistScreen

            assert isinstance(app_with_data.screen, WatchlistScreen)
            assert "new_wl" in app_with_data.screen._watchlist_names

    @pytest.mark.asyncio
    async def test_delete_watchlist_opens_modal(self, app_with_data):
        async with app_with_data.run_test() as pilot:
            await pilot.press("d")
            from caracal.tui.screens.delete_watchlist import DeleteWatchlistModal

            assert isinstance(app_with_data.screen, DeleteWatchlistModal)

    @pytest.mark.asyncio
    async def test_delete_watchlist_confirm(self, app_with_two_watchlists):
        async with app_with_two_watchlists.run_test() as pilot:
            screen = app_with_two_watchlists.screen
            name = screen.current_watchlist
            await pilot.press("d")
            await pilot.click("#confirm-btn")
            await pilot.pause()
            assert name not in app_with_two_watchlists.screen._watchlist_names

    @pytest.mark.asyncio
    async def test_select_watchlist_opens_modal(self, app_with_two_watchlists):
        async with app_with_two_watchlists.run_test() as pilot:
            await pilot.press("w")
            from caracal.tui.screens.watchlist_selector import WatchlistSelectorModal

            assert isinstance(app_with_two_watchlists.screen, WatchlistSelectorModal)

    @pytest.mark.asyncio
    async def test_header_shows_index(self, app_with_two_watchlists):
        async with app_with_two_watchlists.run_test() as pilot:
            screen = app_with_two_watchlists.screen
            assert "(" in screen.sub_title
            assert "/" in screen.sub_title

    @pytest.mark.asyncio
    async def test_delete_on_empty_does_nothing(self, app_no_watchlists):
        async with app_no_watchlists.run_test() as pilot:
            await pilot.press("d")
            from caracal.tui.screens.watchlist import WatchlistScreen

            assert isinstance(app_no_watchlists.screen, WatchlistScreen)

    @pytest.mark.asyncio
    async def test_select_on_empty_does_nothing(self, app_no_watchlists):
        async with app_no_watchlists.run_test() as pilot:
            await pilot.press("w")
            from caracal.tui.screens.watchlist import WatchlistScreen

            assert isinstance(app_no_watchlists.screen, WatchlistScreen)


class TestAddTicker:
    @pytest.mark.asyncio
    async def test_add_ticker_binding_opens_modal(self, app_with_data):
        """Pressing 'a' opens the AddTickerModal."""
        async with app_with_data.run_test() as pilot:
            await pilot.press("a")
            from caracal.tui.screens.add_ticker import AddTickerModal

            assert isinstance(app_with_data.screen, AddTickerModal)

    @pytest.mark.asyncio
    async def test_add_ticker_no_modal_when_no_watchlists(self, app_no_watchlists):
        """Pressing 'a' does nothing when no watchlists exist."""
        async with app_no_watchlists.run_test() as pilot:
            await pilot.press("a")
            from caracal.tui.screens.watchlist import WatchlistScreen

            assert isinstance(app_no_watchlists.screen, WatchlistScreen)


class TestRemoveTicker:
    @pytest.mark.asyncio
    async def test_remove_ticker_binding_opens_modal(self, app_with_data):
        """Pressing 'x' opens the RemoveTickerModal."""
        async with app_with_data.run_test() as pilot:
            await pilot.press("x")
            from caracal.tui.screens.remove_ticker import RemoveTickerModal

            assert isinstance(app_with_data.screen, RemoveTickerModal)

    @pytest.mark.asyncio
    async def test_remove_ticker_no_modal_when_table_empty(self, app_empty_watchlist):
        """Pressing 'x' does nothing when no tickers in watchlist."""
        async with app_empty_watchlist.run_test() as pilot:
            await pilot.press("x")
            from caracal.tui.screens.watchlist import WatchlistScreen

            assert isinstance(app_empty_watchlist.screen, WatchlistScreen)

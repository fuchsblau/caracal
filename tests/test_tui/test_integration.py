"""End-to-end TUI integration tests."""

import pandas as pd
import pytest

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui import CaracalApp
from caracal.tui.data import DataService
from caracal.tui.widgets.watchlist_panel import WatchlistPanel


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
        """Start, show data, enter detail, esc back."""
        async with full_app.run_test() as pilot:
            panel = full_app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            assert table is not None
            assert table.row_count >= 1

            await pilot.press("enter")
            await pilot.pause()
            assert panel.in_detail

            await pilot.press("escape")
            await pilot.pause()
            assert not panel.in_detail

    @pytest.mark.asyncio
    async def test_info_screen(self, full_app):
        """Info screen shows and can be dismissed."""
        async with full_app.run_test() as pilot:
            from caracal.tui.screens.info import InfoScreen

            await pilot.press("i")
            assert isinstance(full_app.screen, InfoScreen)
            await pilot.press("escape")
            # Back to main app screen (not a modal)
            assert not isinstance(full_app.screen, InfoScreen)

    @pytest.mark.asyncio
    async def test_keyboard_navigation(self, full_app):
        """j/k/arrow navigation works."""
        async with full_app.run_test() as pilot:
            await pilot.press("j")
            await pilot.press("k")
            await pilot.press("down")
            await pilot.press("up")

    @pytest.mark.asyncio
    async def test_quit(self, full_app):
        """q quits the app."""
        async with full_app.run_test() as pilot:
            await pilot.press("q")

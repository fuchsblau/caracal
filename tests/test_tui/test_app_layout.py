"""Tests for the new CaracalApp layout."""

import pytest
from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui import CaracalApp
from caracal.tui.data import DataService
from caracal.tui.widgets.watchlist_panel import WatchlistPanel
from caracal.tui.widgets.side_panel import SidePanel
from caracal.tui.widgets.header import CaracalHeader
from caracal.tui.widgets.footer import CaracalFooter


def _make_app_with_data():
    config = CaracalConfig(db_path=":memory:")
    storage = DuckDBStorage(":memory:")
    storage.create_watchlist("tech")
    storage.add_to_watchlist("tech", "AAPL")
    import pandas as pd
    from datetime import date, timedelta
    rows = []
    for i in range(31):
        d = date.today() - timedelta(days=30 - i)
        rows.append({"date": d, "open": 170 + i * 0.1, "high": 172 + i * 0.1,
                      "low": 168 + i * 0.1, "close": 171 + i * 0.1, "volume": 1000000})
    storage.store_ohlcv("AAPL", pd.DataFrame(rows))
    data_service = DataService(config, storage=storage)
    return CaracalApp(config=config, data_service=data_service)


class TestAppLayout:
    @pytest.mark.asyncio
    async def test_has_watchlist_panel(self):
        app = _make_app_with_data()
        async with app.run_test():
            assert app.query_one(WatchlistPanel)

    @pytest.mark.asyncio
    async def test_has_side_panel(self):
        app = _make_app_with_data()
        async with app.run_test():
            side = app.query_one(SidePanel)
            assert not side.display  # collapsed by default

    @pytest.mark.asyncio
    async def test_focused_asset_reactive(self):
        app = _make_app_with_data()
        async with app.run_test():
            assert app.focused_asset is None  # initially None

    @pytest.mark.asyncio
    async def test_drill_down_and_back(self):
        app = _make_app_with_data()
        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            assert panel.in_detail
            await pilot.press("escape")
            await pilot.pause()
            assert not panel.in_detail

    @pytest.mark.asyncio
    async def test_sort_key(self):
        app = _make_app_with_data()
        async with app.run_test() as pilot:
            await pilot.press("s")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            assert table.sort_column is not None

    @pytest.mark.asyncio
    async def test_header_shows_clock(self):
        app = _make_app_with_data()
        async with app.run_test():
            header = app.query_one(CaracalHeader)
            assert header._show_clock is True

    @pytest.mark.asyncio
    async def test_header_icon_is_fisheye(self):
        app = _make_app_with_data()
        async with app.run_test():
            header = app.query_one(CaracalHeader)
            assert header.icon == "◉"

    @pytest.mark.asyncio
    async def test_header_click_does_not_expand(self):
        app = _make_app_with_data()
        async with app.run_test() as pilot:
            header = app.query_one(CaracalHeader)
            await pilot.click(CaracalHeader)
            await pilot.pause()
            assert "-tall" not in header.classes

    @pytest.mark.asyncio
    async def test_watchlist_panel_has_horizontal_padding(self):
        app = _make_app_with_data()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            padding = panel.styles.padding
            assert padding.right == 1
            assert padding.left == 1

    @pytest.mark.asyncio
    async def test_app_uses_caracal_footer(self):
        app = _make_app_with_data()
        async with app.run_test():
            footer = app.query_one(CaracalFooter)
            assert footer is not None

    @pytest.mark.asyncio
    async def test_footer_default_is_dash_for_memory_db(self):
        app = _make_app_with_data()
        async with app.run_test():
            footer = app.query_one(CaracalFooter)
            # In-memory DB has no file mtime
            assert footer.last_updated == "—"

    @pytest.mark.asyncio
    async def test_refresh_updates_footer_timestamp(self):
        app = _make_app_with_data()
        async with app.run_test() as pilot:
            await pilot.press("r")
            await pilot.pause()
            footer = app.query_one(CaracalFooter)
            # After live refresh, timestamp is a full datetime
            assert footer.last_updated != "—"
            assert len(footer.last_updated) == 19  # YYYY-MM-DD HH:MM:SS

    @pytest.mark.asyncio
    async def test_manual_refresh(self):
        app = _make_app_with_data()
        async with app.run_test() as pilot:
            await pilot.press("r")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            assert table.row_count >= 1

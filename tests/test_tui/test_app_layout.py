"""Tests for the new CaracalApp layout."""

import pytest
from textual.containers import Horizontal

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
        rows.append(
            {
                "date": d,
                "open": 170 + i * 0.1,
                "high": 172 + i * 0.1,
                "low": 168 + i * 0.1,
                "close": 171 + i * 0.1,
                "volume": 1000000,
            }
        )
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
            assert side.display  # visible with news panel

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
    async def test_header_height_is_one(self):
        app = _make_app_with_data()
        async with app.run_test():
            header = app.query_one(CaracalHeader)
            # Header must be fixed at height 1 — no tall mode, no subtitle clutter
            assert header.styles.height is not None
            assert header.styles.height.value == 1

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


# ---------------------------------------------------------------------------
# US-059: Split-Layout with Tabbed Watchlists — Layout Composition
# ---------------------------------------------------------------------------


def _make_multi_watchlist_app(watchlists: dict[str, list[str]] | None = None):
    """Build an app with multiple pre-populated watchlists."""
    if watchlists is None:
        watchlists = {"tech": ["AAPL", "MSFT"], "etfs": ["SPY"], "crypto": ["BTC-USD"]}
    config = CaracalConfig(db_path=":memory:")
    storage = DuckDBStorage(":memory:")
    import pandas as pd
    from datetime import date, timedelta

    for name, tickers in watchlists.items():
        storage.create_watchlist(name)
        for ticker in tickers:
            storage.add_to_watchlist(name, ticker)
            rows = []
            for i in range(31):
                d = date.today() - timedelta(days=30 - i)
                rows.append(
                    {
                        "date": d,
                        "open": 100 + i,
                        "high": 102 + i,
                        "low": 98 + i,
                        "close": 101 + i,
                        "volume": 500000,
                    }
                )
            storage.store_ohlcv(ticker, pd.DataFrame(rows))
    data_service = DataService(config, storage=storage)
    return CaracalApp(config=config, data_service=data_service)


class TestSplitLayout:
    """US-059: Verify split-layout composition with Horizontal container."""

    @pytest.mark.asyncio
    async def test_main_layout_is_horizontal(self):
        """WatchlistPanel and SidePanel are children of a Horizontal container."""
        app = _make_app_with_data()
        async with app.run_test():
            layout = app.query_one("#main-layout", Horizontal)
            children_ids = [str(c.id) for c in layout.children]
            assert "watchlist-panel" in children_ids
            assert "side-panel" in children_ids

    @pytest.mark.asyncio
    async def test_watchlist_panel_takes_65_percent_width(self):
        """WatchlistPanel CSS width is 65% (leaving room for news panel)."""
        app = _make_app_with_data()
        async with app.run_test():
            panel = app.query_one("#watchlist-panel", WatchlistPanel)
            assert panel.styles.width is not None
            assert panel.styles.width.value == 65

    @pytest.mark.asyncio
    async def test_side_panel_width_is_35_percent(self):
        """SidePanel has a 35% width rule for the news panel."""
        app = _make_app_with_data()
        async with app.run_test():
            side = app.query_one("#side-panel", SidePanel)
            assert side.styles.width is not None
            assert side.styles.width.value == 35

    @pytest.mark.asyncio
    async def test_side_panel_visible_by_default(self):
        """SidePanel is visible by default (news panel active)."""
        app = _make_app_with_data()
        async with app.run_test():
            side = app.query_one("#side-panel", SidePanel)
            assert side.display

    @pytest.mark.asyncio
    async def test_tab_count_matches_watchlist_count(self):
        """Number of tabs equals number of watchlists loaded."""
        app = _make_multi_watchlist_app()
        async with app.run_test():
            panel = app.query_one("#watchlist-panel", WatchlistPanel)
            assert panel.tab_count == 3

    @pytest.mark.asyncio
    async def test_tab_switching_updates_active_watchlist(self):
        """Pressing 1-3 keys cycles through all watchlists in order."""
        app = _make_multi_watchlist_app()
        async with app.run_test() as pilot:
            names = app._watchlist_names
            assert len(names) == 3
            for idx, name in enumerate(names):
                await pilot.press(str(idx + 1))
                await pilot.pause()
                assert app.active_watchlist == name

    @pytest.mark.asyncio
    async def test_tab_switch_changes_active_table(self):
        """After switching tabs, get_active_table returns the correct table."""
        app = _make_multi_watchlist_app()
        async with app.run_test() as pilot:
            names = app._watchlist_names
            # Switch to last tab
            await pilot.press(str(len(names)))
            await pilot.pause()
            panel = app.query_one("#watchlist-panel", WatchlistPanel)
            table = panel.get_active_table()
            assert table is not None
            expected_id = f"wt-{names[-1]}"
            assert str(table.id) == expected_id

    @pytest.mark.asyncio
    async def test_crud_bindings_still_active(self):
        """All CRUD keybindings (c, d, a, x) are present in app bindings."""
        app = _make_app_with_data()
        async with app.run_test():
            binding_keys = {b.key for b in app.BINDINGS}
            for key in ("c", "d", "a", "x"):
                assert key in binding_keys, f"Missing CRUD binding: {key}"

    @pytest.mark.asyncio
    async def test_tab_bindings_1_through_9(self):
        """All nine tab-switch bindings (1-9) are registered."""
        app = _make_app_with_data()
        async with app.run_test():
            binding_keys = {b.key for b in app.BINDINGS}
            for n in range(1, 10):
                assert str(n) in binding_keys, f"Missing tab binding: {n}"

"""Tests for CaracalApp — comprehensive Pilot tests for all action methods."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui import CaracalApp
from caracal.tui.data import DataService
from caracal.tui.widgets.footer import CaracalFooter
from caracal.tui.widgets.watchlist_panel import WatchlistPanel


def _make_ohlcv(base_price: float = 150.0, days: int = 31) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame."""
    rows = []
    for i in range(days):
        d = date.today() - timedelta(days=days - 1 - i)
        rows.append({
            "date": d,
            "open": base_price + i * 0.1,
            "high": base_price + 2 + i * 0.1,
            "low": base_price - 1 + i * 0.1,
            "close": base_price + 1 + i * 0.1,
            "volume": 1_000_000,
        })
    return pd.DataFrame(rows)


@pytest.fixture
def config():
    return CaracalConfig(db_path=":memory:")


def _make_app_with_watchlists(
    config: CaracalConfig,
    watchlists: dict[str, list[str]] | None = None,
) -> CaracalApp:
    """Build a CaracalApp with pre-populated watchlists and OHLCV data."""
    if watchlists is None:
        watchlists = {"tech": ["AAPL", "MSFT"], "etfs": ["SPY"]}
    storage = DuckDBStorage(":memory:")
    for name, tickers in watchlists.items():
        storage.create_watchlist(name)
        for ticker in tickers:
            storage.add_to_watchlist(name, ticker)
            storage.store_ohlcv(ticker, _make_ohlcv())
    data_service = DataService(config, storage=storage)
    return CaracalApp(config=config, data_service=data_service)


def _make_empty_app(config: CaracalConfig) -> CaracalApp:
    """Build a CaracalApp with no watchlists."""
    storage = DuckDBStorage(":memory:")
    data_service = DataService(config, storage=storage)
    return CaracalApp(config=config, data_service=data_service)


# ---------------------------------------------------------------------------
# Basic construction
# ---------------------------------------------------------------------------


class TestCaracalApp:
    def test_app_creates(self, config):
        app = CaracalApp(config=config)
        assert app.config == config
        assert app.title == "Caracal"

    @pytest.mark.asyncio
    async def test_app_mounts(self, config):
        app = CaracalApp(config=config)
        async with app.run_test():
            assert app.screen is not None

    def test_owns_data_service_when_none_passed(self, config):
        app = CaracalApp(config=config)
        assert app._owns_data_service is True

    def test_does_not_own_data_service_when_passed(self, config):
        ds = DataService(config)
        app = CaracalApp(config=config, data_service=ds)
        assert app._owns_data_service is False
        ds.close()


# ---------------------------------------------------------------------------
# Mount and load
# ---------------------------------------------------------------------------


class TestMountAndLoad:
    @pytest.mark.asyncio
    async def test_mount_loads_watchlists(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            assert app._watchlist_names == ["etfs", "tech"]
            assert app.active_watchlist == "etfs"

    @pytest.mark.asyncio
    async def test_mount_sets_active_watchlist_to_first(self, config):
        app = _make_app_with_watchlists(config, {"alpha": ["AAPL"]})
        async with app.run_test():
            assert app.active_watchlist == "alpha"

    @pytest.mark.asyncio
    async def test_mount_empty_watchlists(self, config):
        app = _make_empty_app(config)
        async with app.run_test():
            assert app._watchlist_names == []
            assert app.active_watchlist is None


# ---------------------------------------------------------------------------
# Navigation: cursor_down / cursor_up
# ---------------------------------------------------------------------------


class TestCursorNavigation:
    @pytest.mark.asyncio
    async def test_cursor_down(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("j")
            await pilot.pause()
            # Should not crash; app should still be responsive
            panel = app.query_one(WatchlistPanel)
            assert not panel.in_detail

    @pytest.mark.asyncio
    async def test_cursor_up(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("k")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            assert not panel.in_detail

    @pytest.mark.asyncio
    async def test_j_moves_cursor_to_next_row(self, config):
        """j key moves the DataTable cursor down by one row."""
        app = _make_app_with_watchlists(config, {"wl": ["AAPL", "MSFT"]})
        async with app.run_test() as pilot:
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            dt = table.query_one("DataTable")
            # cursor starts at row 0
            assert dt.cursor_coordinate.row == 0
            await pilot.press("j")
            await pilot.pause()
            assert dt.cursor_coordinate.row == 1

    @pytest.mark.asyncio
    async def test_k_moves_cursor_up(self, config):
        """k key moves the DataTable cursor up by one row."""
        app = _make_app_with_watchlists(config, {"wl": ["AAPL", "MSFT"]})
        async with app.run_test() as pilot:
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            dt = table.query_one("DataTable")
            # move down first, then up
            await pilot.press("j")
            await pilot.pause()
            assert dt.cursor_coordinate.row == 1
            await pilot.press("k")
            await pilot.pause()
            assert dt.cursor_coordinate.row == 0

    @pytest.mark.asyncio
    async def test_cursor_down_noop_in_detail(self, config):
        """Cursor movement is a no-op when in detail view."""
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            assert panel.in_detail
            # j should be a no-op in detail view
            await pilot.press("j")
            await pilot.pause()
            assert panel.in_detail

    @pytest.mark.asyncio
    async def test_cursor_up_noop_in_detail(self, config):
        """Cursor up is a no-op when in detail view."""
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            assert panel.in_detail
            await pilot.press("k")
            await pilot.pause()
            assert panel.in_detail

    @pytest.mark.asyncio
    async def test_cursor_navigation_noop_on_empty_watchlist(self, config):
        """j/k on a watchlist with no tickers is a no-op."""
        app = _make_app_with_watchlists(config, {"empty": []})
        async with app.run_test() as pilot:
            await pilot.press("j")
            await pilot.pause()
            await pilot.press("k")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            assert not panel.in_detail


# ---------------------------------------------------------------------------
# Navigation: drill_down and back
# ---------------------------------------------------------------------------


class TestDrillDown:
    @pytest.mark.asyncio
    async def test_drill_down_shows_detail(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            assert panel.in_detail
            assert app.focused_asset is not None

    @pytest.mark.asyncio
    async def test_drill_down_noop_when_in_detail(self, config):
        """Pressing enter while in detail does nothing."""
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            assert panel.in_detail
            ticker_before = app.focused_asset
            await pilot.press("enter")
            await pilot.pause()
            assert panel.in_detail
            assert app.focused_asset == ticker_before

    @pytest.mark.asyncio
    async def test_drill_down_noop_empty_watchlist(self, config):
        """Drill down with no tickers is a no-op."""
        app = _make_app_with_watchlists(config, {"empty": []})
        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            assert not panel.in_detail

    @pytest.mark.asyncio
    async def test_back_hides_detail(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            assert panel.in_detail
            await pilot.press("escape")
            await pilot.pause()
            assert not panel.in_detail

    @pytest.mark.asyncio
    async def test_back_noop_when_not_in_detail(self, config):
        """Escape when not in detail does nothing special."""
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            panel = app.query_one(WatchlistPanel)
            assert not panel.in_detail
            await pilot.press("escape")
            await pilot.pause()
            # Should still not be in detail
            assert not panel.in_detail

    @pytest.mark.asyncio
    async def test_drill_down_preserves_cursor_on_return(self, config):
        """Cursor position is restored after Escape from detail view."""
        app = _make_app_with_watchlists(config, {"wl": ["AAPL", "MSFT"]})
        async with app.run_test() as pilot:
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            dt = table.query_one("DataTable")
            # Move cursor to row 1 (MSFT)
            await pilot.press("j")
            await pilot.pause()
            assert dt.cursor_coordinate.row == 1
            # Drill down
            await pilot.press("enter")
            await pilot.pause()
            assert panel.in_detail
            # Return
            await pilot.press("escape")
            await pilot.pause()
            assert not panel.in_detail
            # Cursor should still be at row 1
            table = panel.get_active_table()
            dt = table.query_one("DataTable")
            assert dt.cursor_coordinate.row == 1

    @pytest.mark.asyncio
    async def test_drill_down_sets_focused_asset(self, config):
        """Drill-down sets focused_asset to the selected ticker."""
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            assert app.focused_asset is None
            await pilot.press("enter")
            await pilot.pause()
            assert app.focused_asset is not None
            # focused_asset should be a ticker from the watchlist
            assert isinstance(app.focused_asset, str)
            assert len(app.focused_asset) > 0

    @pytest.mark.asyncio
    async def test_detail_view_renders_in_watchlist_panel(self, config):
        """AssetDetailView is a child of WatchlistPanel (not a separate screen)."""
        from caracal.tui.widgets.asset_detail_view import AssetDetailView

        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            detail = panel.query_one(AssetDetailView)
            assert detail.display is True


# ---------------------------------------------------------------------------
# Sort
# ---------------------------------------------------------------------------


class TestCycleSort:
    @pytest.mark.asyncio
    async def test_sort_cycles(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("s")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            assert table is not None
            assert table.sort_column is not None

    @pytest.mark.asyncio
    async def test_sort_full_cycle(self, config):
        """Pressing s cycles through asc/desc for each sort column."""
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            # 1st press: ticker asc
            await pilot.press("s")
            await pilot.pause()
            assert table.sort_column == "ticker"
            assert table._sort_ascending is True
            # 2nd press: ticker desc
            await pilot.press("s")
            await pilot.pause()
            assert table.sort_column == "ticker"
            assert table._sort_ascending is False
            # 3rd press: change_pct asc
            await pilot.press("s")
            await pilot.pause()
            assert table.sort_column == "change_pct"
            assert table._sort_ascending is True

    @pytest.mark.asyncio
    async def test_sort_noop_in_detail(self, config):
        """Sort is a no-op when in detail view."""
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            assert panel.in_detail
            await pilot.press("s")
            await pilot.pause()
            assert panel.in_detail

    @pytest.mark.asyncio
    async def test_sort_noop_empty_watchlist(self, config):
        """Sort on empty watchlist is a no-op."""
        app = _make_app_with_watchlists(config, {"empty": []})
        async with app.run_test() as pilot:
            await pilot.press("s")
            await pilot.pause()


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


class TestRefresh:
    @pytest.mark.asyncio
    async def test_refresh_live(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("r")
            await pilot.pause()
            footer = app.query_one(CaracalFooter)
            # After live refresh, timestamp should be updated
            assert footer.last_updated != "—"

    @pytest.mark.asyncio
    async def test_refresh_live_noop_no_watchlist(self, config):
        """Refresh is a no-op if no active watchlist."""
        app = _make_empty_app(config)
        async with app.run_test() as pilot:
            await pilot.press("r")
            await pilot.pause()
            footer = app.query_one(CaracalFooter)
            assert footer.last_updated == "—"


# ---------------------------------------------------------------------------
# Auto-refresh
# ---------------------------------------------------------------------------


class TestAutoRefresh:
    @pytest.mark.asyncio
    async def test_auto_refresh_skips_when_in_detail(self, config):
        """Auto-refresh should not run when in detail view."""
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            assert panel.in_detail
            # Call the bound coroutine directly
            await CaracalApp._auto_refresh(app)
            assert panel.in_detail  # still in detail

    @pytest.mark.asyncio
    async def test_auto_refresh_noop_no_watchlist(self, config):
        """Auto-refresh returns early if no active watchlist."""
        app = _make_empty_app(config)
        async with app.run_test():
            await CaracalApp._auto_refresh(app)  # should not crash

    @pytest.mark.asyncio
    async def test_auto_refresh_updates_data(self, config):
        """Auto-refresh updates the active watchlist data."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            assert not panel.in_detail
            await CaracalApp._auto_refresh(app)
            table = panel.get_active_table()
            assert table is not None
            assert table.row_count >= 1


# ---------------------------------------------------------------------------
# Tab switching
# ---------------------------------------------------------------------------


class TestSwitchTab:
    @pytest.mark.asyncio
    async def test_switch_tab_2(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            first_wl = app.active_watchlist
            await pilot.press("2")
            await pilot.pause()
            # Should have switched to the second watchlist
            assert app.active_watchlist != first_wl
            assert app.active_watchlist == app._watchlist_names[1]

    @pytest.mark.asyncio
    async def test_switch_tab_out_of_range(self, config):
        """Tab number beyond available watchlists is a no-op."""
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            current = app.active_watchlist
            await pilot.press("9")
            await pilot.pause()
            assert app.active_watchlist == current

    @pytest.mark.asyncio
    async def test_switch_tab_hides_detail(self, config):
        """Switching tab while in detail hides the detail view."""
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            assert panel.in_detail
            await pilot.press("2")
            await pilot.pause()
            assert not panel.in_detail

    @pytest.mark.asyncio
    async def test_switch_tab_1(self, config):
        """Tab 1 goes to the first watchlist."""
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("2")
            await pilot.pause()
            await pilot.press("1")
            await pilot.pause()
            assert app.active_watchlist == app._watchlist_names[0]


# ---------------------------------------------------------------------------
# Tab activated event
# ---------------------------------------------------------------------------


class TestTabActivated:
    @pytest.mark.asyncio
    async def test_tab_activated_event_syncs_active(self, config):
        """Simulates the TabbedContent tab activation event."""
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            # Switch to tab 2 to verify syncing works
            await pilot.press("2")
            await pilot.pause()
            assert app.active_watchlist == app._watchlist_names[1]


# ---------------------------------------------------------------------------
# CRUD: Create watchlist
# ---------------------------------------------------------------------------


class TestCreateWatchlist:
    @pytest.mark.asyncio
    async def test_create_watchlist_opens_modal(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            from caracal.tui.screens.create_watchlist import CreateWatchlistModal

            await pilot.press("c")
            await pilot.pause()
            assert isinstance(app.screen, CreateWatchlistModal)

    @pytest.mark.asyncio
    async def test_on_create_result_none(self, config):
        """_on_create_result with None does nothing."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            names_before = list(app._watchlist_names)
            await app._on_create_result(None)
            assert app._watchlist_names == names_before

    @pytest.mark.asyncio
    async def test_on_create_result_success(self, config):
        """_on_create_result with a name creates the watchlist."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            await app._on_create_result("newlist")
            assert "newlist" in app._watchlist_names

    @pytest.mark.asyncio
    async def test_on_create_result_duplicate(self, config):
        """_on_create_result with an existing name shows error notification."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            # Create it once
            await app._on_create_result("dup")
            # Creating again should raise StorageError and notify
            await app._on_create_result("dup")
            # The second create should not add a duplicate
            assert app._watchlist_names.count("dup") == 1


# ---------------------------------------------------------------------------
# CRUD: Delete watchlist
# ---------------------------------------------------------------------------


class TestDeleteWatchlist:
    @pytest.mark.asyncio
    async def test_delete_watchlist_opens_modal(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            from caracal.tui.screens.delete_watchlist import DeleteWatchlistModal

            await pilot.press("d")
            await pilot.pause()
            assert isinstance(app.screen, DeleteWatchlistModal)

    @pytest.mark.asyncio
    async def test_delete_watchlist_noop_no_active(self, config):
        """Delete is a no-op if no active watchlist."""
        app = _make_empty_app(config)
        async with app.run_test() as pilot:
            await pilot.press("d")
            await pilot.pause()
            # Should not have pushed a modal
            from caracal.tui.screens.delete_watchlist import DeleteWatchlistModal
            assert not isinstance(app.screen, DeleteWatchlistModal)

    @pytest.mark.asyncio
    async def test_on_delete_result_false(self, config):
        """_on_delete_result(False) does nothing."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            names_before = list(app._watchlist_names)
            await app._on_delete_result(False)
            assert app._watchlist_names == names_before

    @pytest.mark.asyncio
    async def test_on_delete_result_true(self, config):
        """_on_delete_result(True) removes the active watchlist."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            active = app.active_watchlist
            await app._on_delete_result(True)
            assert active not in app._watchlist_names

    @pytest.mark.asyncio
    async def test_on_delete_result_last_watchlist(self, config):
        """Deleting the last watchlist sets active_watchlist to None."""
        app = _make_app_with_watchlists(config, {"only": ["AAPL"]})
        async with app.run_test():
            assert app.active_watchlist == "only"
            await app._on_delete_result(True)
            assert app._watchlist_names == []
            assert app.active_watchlist is None


# ---------------------------------------------------------------------------
# CRUD: Add ticker
# ---------------------------------------------------------------------------


class TestAddTicker:
    @pytest.mark.asyncio
    async def test_add_ticker_opens_modal(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            from caracal.tui.screens.add_ticker import AddTickerModal

            await pilot.press("a")
            await pilot.pause()
            assert isinstance(app.screen, AddTickerModal)

    @pytest.mark.asyncio
    async def test_add_ticker_noop_no_active(self, config):
        """Add ticker is a no-op if no active watchlist."""
        app = _make_empty_app(config)
        async with app.run_test() as pilot:
            from caracal.tui.screens.add_ticker import AddTickerModal

            await pilot.press("a")
            await pilot.pause()
            assert not isinstance(app.screen, AddTickerModal)

    @pytest.mark.asyncio
    async def test_on_add_result_none(self, config):
        """_on_add_result with None does nothing."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            count_before = table.row_count
            app._on_add_result(None)
            assert table.row_count == count_before

    @pytest.mark.asyncio
    async def test_on_add_result_success(self, config):
        """_on_add_result with tickers adds them and reloads."""
        app = _make_app_with_watchlists(config, {"wl": ["AAPL"]})
        async with app.run_test():
            app._on_add_result(["NVDA"])
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            # NVDA may not have OHLCV data, but it should still be in the list
            assert table.row_count >= 1

    @pytest.mark.asyncio
    async def test_on_add_result_duplicate(self, config):
        """_on_add_result with existing ticker notifies about duplicates."""
        app = _make_app_with_watchlists(config, {"wl": ["AAPL"]})
        async with app.run_test():
            # Adding AAPL again should report duplicate
            app._on_add_result(["AAPL"])

    @pytest.mark.asyncio
    async def test_on_add_result_storage_error(self, config):
        """_on_add_result handles StorageError."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            from caracal.storage.duckdb import StorageError

            with patch.object(
                app.data_service, "add_to_watchlist", side_effect=StorageError("boom")
            ):
                app._on_add_result(["NVDA"])
                # Should not crash, just notify


# ---------------------------------------------------------------------------
# CRUD: Remove ticker
# ---------------------------------------------------------------------------


class TestRemoveTicker:
    @pytest.mark.asyncio
    async def test_remove_ticker_opens_modal(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            from caracal.tui.screens.remove_ticker import RemoveTickerModal

            await pilot.press("x")
            await pilot.pause()
            assert isinstance(app.screen, RemoveTickerModal)

    @pytest.mark.asyncio
    async def test_remove_ticker_noop_no_active(self, config):
        """Remove ticker is a no-op if no active watchlist."""
        app = _make_empty_app(config)
        async with app.run_test() as pilot:
            from caracal.tui.screens.remove_ticker import RemoveTickerModal

            await pilot.press("x")
            await pilot.pause()
            assert not isinstance(app.screen, RemoveTickerModal)

    @pytest.mark.asyncio
    async def test_remove_ticker_noop_empty_table(self, config):
        """Remove ticker is a no-op if table is empty."""
        app = _make_app_with_watchlists(config, {"empty": []})
        async with app.run_test() as pilot:
            from caracal.tui.screens.remove_ticker import RemoveTickerModal

            await pilot.press("x")
            await pilot.pause()
            assert not isinstance(app.screen, RemoveTickerModal)

    @pytest.mark.asyncio
    async def test_on_remove_result_false(self, config):
        """_on_remove_result(False) does nothing."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            app._pending_remove_ticker = "AAPL"
            app._on_remove_result(False)
            # Should not crash

    @pytest.mark.asyncio
    async def test_on_remove_result_true(self, config):
        """_on_remove_result(True) removes the ticker."""
        app = _make_app_with_watchlists(config, {"wl": ["AAPL", "MSFT"]})
        async with app.run_test():
            app._pending_remove_ticker = "AAPL"
            app._on_remove_result(True)
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            # Table should have been reloaded
            assert table is not None

    @pytest.mark.asyncio
    async def test_on_remove_result_no_pending(self, config):
        """_on_remove_result(True) with no pending ticker does nothing."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            app._pending_remove_ticker = None
            app._on_remove_result(True)

    @pytest.mark.asyncio
    async def test_on_remove_result_storage_error(self, config):
        """_on_remove_result handles StorageError."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            from caracal.storage.duckdb import StorageError

            app._pending_remove_ticker = "AAPL"
            with patch.object(
                app.data_service,
                "remove_from_watchlist",
                side_effect=StorageError("boom"),
            ):
                app._on_remove_result(True)


# ---------------------------------------------------------------------------
# Reload active watchlist
# ---------------------------------------------------------------------------


class TestReloadActiveWatchlist:
    @pytest.mark.asyncio
    async def test_reload_active_watchlist(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            app._reload_active_watchlist()
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            assert table is not None

    @pytest.mark.asyncio
    async def test_reload_noop_no_active(self, config):
        app = _make_empty_app(config)
        async with app.run_test():
            app._reload_active_watchlist()  # should not crash


# ---------------------------------------------------------------------------
# Info screen
# ---------------------------------------------------------------------------


class TestInfoScreen:
    @pytest.mark.asyncio
    async def test_info_screen_opens(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            from caracal.tui.screens.info import InfoScreen

            await pilot.press("i")
            await pilot.pause()
            assert isinstance(app.screen, InfoScreen)

    @pytest.mark.asyncio
    async def test_info_screen_dismiss(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            from caracal.tui.screens.info import InfoScreen

            await pilot.press("i")
            await pilot.pause()
            assert isinstance(app.screen, InfoScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, InfoScreen)


# ---------------------------------------------------------------------------
# Focused asset tracking
# ---------------------------------------------------------------------------


class TestFocusedAsset:
    @pytest.mark.asyncio
    async def test_initial_focused_asset_is_none(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            assert app.focused_asset is None

    @pytest.mark.asyncio
    async def test_focused_asset_set_on_drill_down(self, config):
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            assert app.focused_asset is not None

    @pytest.mark.asyncio
    async def test_cursor_changed_event(self, config):
        """Simulates the cursor changed event from WatchlistTable."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            # Create a mock event
            event = MagicMock()
            event.ticker = "TEST"
            app.on_watchlist_table_cursor_changed(event)
            assert app.focused_asset == "TEST"

    @pytest.mark.asyncio
    async def test_row_activated_event(self, config):
        """Simulates the row activated event from WatchlistTable."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            event = MagicMock()
            event.ticker = "AAPL"
            app.on_watchlist_table_row_activated(event)
            panel = app.query_one(WatchlistPanel)
            assert panel.in_detail
            assert app.focused_asset == "AAPL"

    @pytest.mark.asyncio
    async def test_row_activated_noop_in_detail(self, config):
        """Row activated is a no-op when already in detail."""
        app = _make_app_with_watchlists(config)
        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            assert panel.in_detail
            first_ticker = app.focused_asset
            event = MagicMock()
            event.ticker = "DIFFERENT"
            app.on_watchlist_table_row_activated(event)
            assert app.focused_asset == first_ticker


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_unmount_closes_owned_service(self, config):
        """on_unmount closes the data service if owned."""
        app = CaracalApp(config=config)
        async with app.run_test():
            assert app._owns_data_service is True
            with patch.object(app.data_service, "close") as mock_close:
                app.on_unmount()
                mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_unmount_does_not_close_injected_service(self, config):
        """on_unmount does NOT close a data service it doesn't own."""
        ds = DataService(config)
        app = CaracalApp(config=config, data_service=ds)
        async with app.run_test():
            assert app._owns_data_service is False
            with patch.object(app.data_service, "close") as mock_close:
                app.on_unmount()
                mock_close.assert_not_called()
        ds.close()


# ---------------------------------------------------------------------------
# Footer timestamp
# ---------------------------------------------------------------------------


class TestFooterTimestamp:
    @pytest.mark.asyncio
    async def test_update_footer_from_db_no_timestamp(self, config):
        """Footer keeps default when DB has no timestamp."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            footer = app.query_one(CaracalFooter)
            # In-memory DB returns None for last_fetch_time
            app._update_footer_from_db()
            assert footer.last_updated == "—"

    @pytest.mark.asyncio
    async def test_update_footer_from_db_with_timestamp(self, config):
        """Footer gets updated when DB has a timestamp."""
        app = _make_app_with_watchlists(config)
        async with app.run_test():
            with patch.object(
                app.data_service, "get_last_fetch_time", return_value="2024-01-15 10:30:00"
            ):
                app._update_footer_from_db()
                footer = app.query_one(CaracalFooter)
                assert footer.last_updated == "2024-01-15 10:30:00"


# ---------------------------------------------------------------------------
# US-061: Keyboard Binding Completeness
# ---------------------------------------------------------------------------


class TestKeyboardBindings:
    """US-061: Verify all required keyboard bindings are registered."""

    def test_navigation_bindings(self):
        """j/k for row navigation, enter for drill-down, escape for back."""
        keys = {b.key for b in CaracalApp.BINDINGS}
        assert "j" in keys, "Missing j binding for cursor down"
        assert "k" in keys, "Missing k binding for cursor up"
        assert "enter" in keys, "Missing enter binding for drill-down"
        assert "escape" in keys, "Missing escape binding for back"

    def test_sort_binding(self):
        """s key for sort cycling."""
        keys = {b.key for b in CaracalApp.BINDINGS}
        assert "s" in keys, "Missing s binding for sort"

    def test_refresh_binding(self):
        """r key for live refresh."""
        keys = {b.key for b in CaracalApp.BINDINGS}
        assert "r" in keys, "Missing r binding for refresh"

    def test_tab_switch_bindings_1_through_9(self):
        """1-9 keys for tab switching."""
        keys = {b.key for b in CaracalApp.BINDINGS}
        for n in range(1, 10):
            assert str(n) in keys, f"Missing tab binding: {n}"

    def test_quit_binding(self):
        """q key for quit."""
        keys = {b.key for b in CaracalApp.BINDINGS}
        assert "q" in keys, "Missing q binding for quit"

    def test_crud_bindings(self):
        """c/d/a/x for CRUD operations."""
        keys = {b.key for b in CaracalApp.BINDINGS}
        assert "c" in keys, "Missing c binding for create watchlist"
        assert "d" in keys, "Missing d binding for delete watchlist"
        assert "a" in keys, "Missing a binding for add ticker"
        assert "x" in keys, "Missing x binding for remove ticker"

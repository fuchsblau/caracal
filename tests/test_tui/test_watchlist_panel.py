"""Tests for WatchlistPanel widget."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import TabPane, TabbedContent

from caracal.tui.widgets.watchlist_panel import WatchlistPanel
from caracal.tui.widgets.watchlist_table import WatchlistTable
from caracal.tui.widgets.asset_detail_view import AssetDetailView


def _make_watchlist_row(ticker: str, **overrides) -> dict:
    """Build a minimal watchlist row with sensible defaults."""
    row = {
        "ticker": ticker,
        "close": 100.0,
        "change_pct": 0.0,
        "signal": "hold",
        "confidence": 0.5,
        "rsi": 50.0,
        "macd_interpretation": "neutral",
        "bb_position": "neutral",
    }
    row.update(overrides)
    return row


SAMPLE_DATA = {
    "tech": [
        {
            "ticker": "AAPL",
            "close": 175.5,
            "change_pct": 2.3,
            "signal": "buy",
            "confidence": 0.85,
            "rsi": 65.0,
            "macd_interpretation": "bull",
            "bb_position": "neutral",
        },
    ],
    "energy": [
        {
            "ticker": "XOM",
            "close": 110.0,
            "change_pct": -0.5,
            "signal": "hold",
            "confidence": 0.4,
            "rsi": 50.0,
            "macd_interpretation": "bear",
            "bb_position": "neutral",
        },
    ],
}


class PanelTestApp(App):
    def compose(self) -> ComposeResult:
        yield WatchlistPanel()

    async def on_mount(self) -> None:
        panel = self.query_one(WatchlistPanel)
        await panel.load_watchlists(SAMPLE_DATA)


class TestWatchlistPanel:
    @pytest.mark.asyncio
    async def test_creates_tabs_for_watchlists(self):
        app = PanelTestApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            assert panel.tab_count == 2

    @pytest.mark.asyncio
    async def test_detail_view_hidden_by_default(self):
        app = PanelTestApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            detail = panel.query_one(AssetDetailView)
            assert not detail.display

    @pytest.mark.asyncio
    async def test_drill_down_shows_detail(self):
        app = PanelTestApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            detail_data = {
                "ticker": "AAPL",
                "close": 175.5,
                "change_pct": 2.3,
                "signal": "buy",
                "confidence": 0.85,
                "indicators": {"rsi_14": 65.0},
                "ohlcv": [],
            }
            panel.show_detail(detail_data)
            detail = panel.query_one(AssetDetailView)
            assert detail.display
            tabs = panel.query_one(TabbedContent)
            assert not tabs.display

    @pytest.mark.asyncio
    async def test_hide_detail_restores_tabs(self):
        app = PanelTestApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            detail_data = {
                "ticker": "AAPL",
                "close": 175.5,
                "change_pct": 2.3,
                "signal": "buy",
                "confidence": 0.85,
                "indicators": {},
                "ohlcv": [],
            }
            panel.show_detail(detail_data)
            panel.hide_detail()
            detail = panel.query_one(AssetDetailView)
            assert not detail.display
            tabs = panel.query_one(TabbedContent)
            assert tabs.display


# ---------------------------------------------------------------------------
# US-059: Split-Layout with Tabbed Watchlists
# ---------------------------------------------------------------------------


class _SingleWatchlistApp(App):
    """App with exactly one watchlist for tab count verification."""

    def compose(self) -> ComposeResult:
        yield WatchlistPanel()

    async def on_mount(self) -> None:
        panel = self.query_one(WatchlistPanel)
        await panel.load_watchlists({"only": [_make_watchlist_row("AAPL")]})


class _ThreeWatchlistApp(App):
    """App with three watchlists for tab count verification."""

    def compose(self) -> ComposeResult:
        yield WatchlistPanel()

    async def on_mount(self) -> None:
        panel = self.query_one(WatchlistPanel)
        await panel.load_watchlists({
            "tech": [_make_watchlist_row("AAPL")],
            "energy": [_make_watchlist_row("XOM")],
            "finance": [_make_watchlist_row("JPM")],
        })


class _EmptyWatchlistsApp(App):
    """App with no watchlists."""

    def compose(self) -> ComposeResult:
        yield WatchlistPanel()

    async def on_mount(self) -> None:
        panel = self.query_one(WatchlistPanel)
        await panel.load_watchlists({})


class TestTabbedWatchlistLayout:
    """US-059: Verify dynamic tab creation per watchlist."""

    @pytest.mark.asyncio
    async def test_single_watchlist_creates_one_tab(self):
        """One watchlist produces exactly one tab."""
        app = _SingleWatchlistApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            assert panel.tab_count == 1

    @pytest.mark.asyncio
    async def test_three_watchlists_create_three_tabs(self):
        """Three watchlists produce exactly three tabs."""
        app = _ThreeWatchlistApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            assert panel.tab_count == 3

    @pytest.mark.asyncio
    async def test_zero_watchlists_create_zero_tabs(self):
        """No watchlists produce zero tabs."""
        app = _EmptyWatchlistsApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            assert panel.tab_count == 0

    @pytest.mark.asyncio
    async def test_each_tab_contains_watchlist_table(self):
        """Every tab pane contains a WatchlistTable widget."""
        app = _ThreeWatchlistApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            tc = panel.query_one(TabbedContent)
            panes = tc.query(TabPane)
            assert len(list(panes)) == 3
            for pane in panes:
                tables = pane.query(WatchlistTable)
                assert len(list(tables)) == 1

    @pytest.mark.asyncio
    async def test_tab_pane_ids_match_watchlist_names(self):
        """Tab pane IDs follow the tab-{name} convention."""
        app = _ThreeWatchlistApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            tc = panel.query_one(TabbedContent)
            pane_ids = {str(pane.id) for pane in tc.query(TabPane)}
            assert pane_ids == {"tab-tech", "tab-energy", "tab-finance"}

    @pytest.mark.asyncio
    async def test_watchlist_table_ids_match_names(self):
        """WatchlistTable IDs follow the wt-{name} convention."""
        app = _ThreeWatchlistApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            table_ids = {
                str(t.id) for t in panel.query(WatchlistTable)
            }
            assert table_ids == {"wt-tech", "wt-energy", "wt-finance"}

    @pytest.mark.asyncio
    async def test_get_active_table_returns_watchlist_table(self):
        """get_active_table returns a WatchlistTable for the active tab."""
        app = PanelTestApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            assert isinstance(table, WatchlistTable)

    @pytest.mark.asyncio
    async def test_get_active_table_none_when_no_tabs(self):
        """get_active_table returns None when there are no tabs."""
        app = _EmptyWatchlistsApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            assert table is None

    @pytest.mark.asyncio
    async def test_reload_clears_and_recreates_tabs(self):
        """Calling load_watchlists again replaces all tabs."""
        app = PanelTestApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            assert panel.tab_count == 2
            # Reload with 3 watchlists
            await panel.load_watchlists({
                "a": [_make_watchlist_row("A")],
                "b": [_make_watchlist_row("B")],
                "c": [_make_watchlist_row("C")],
            })
            assert panel.tab_count == 3

    @pytest.mark.asyncio
    async def test_refresh_watchlist_updates_table_data(self):
        """refresh_watchlist updates the table in the matching tab."""
        app = PanelTestApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            # Add a second ticker to the 'tech' watchlist
            new_rows = [
                _make_watchlist_row("AAPL"),
                _make_watchlist_row("MSFT"),
            ]
            panel.refresh_watchlist("tech", new_rows)
            table = panel.query_one("#wt-tech", WatchlistTable)
            assert table.row_count == 2

    @pytest.mark.asyncio
    async def test_refresh_nonexistent_watchlist_is_noop(self):
        """refresh_watchlist with unknown name does not crash."""
        app = PanelTestApp()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            # This should not raise
            panel.refresh_watchlist("nonexistent", [_make_watchlist_row("X")])

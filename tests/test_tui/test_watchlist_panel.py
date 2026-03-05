"""Tests for WatchlistPanel widget."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import TabbedContent

from caracal.tui.widgets.watchlist_panel import WatchlistPanel
from caracal.tui.widgets.watchlist_table import WatchlistTable
from caracal.tui.widgets.asset_detail_view import AssetDetailView


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

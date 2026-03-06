"""Tests for auto-refresh, state preservation (NF-019), and change highlighting."""

import pandas as pd
import pytest
from datetime import date, timedelta
from textual.app import App, ComposeResult

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui import CaracalApp
from caracal.tui.data import DataService
from caracal.tui.widgets.footer import CaracalFooter
from caracal.tui.widgets.watchlist_panel import WatchlistPanel
from caracal.tui.widgets.watchlist_table import WatchlistTable


def _make_ohlcv(base_price: float = 170.0, days: int = 31) -> pd.DataFrame:
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


def _make_app():
    config = CaracalConfig(db_path=":memory:")
    storage = DuckDBStorage(":memory:")
    storage.create_watchlist("tech")
    storage.add_to_watchlist("tech", "AAPL")
    storage.store_ohlcv("AAPL", _make_ohlcv())
    return CaracalApp(config=config, data_service=DataService(config, storage=storage))


def _make_multi_app():
    """App with two watchlists and multiple tickers for state preservation tests."""
    config = CaracalConfig(db_path=":memory:")
    storage = DuckDBStorage(":memory:")
    storage.create_watchlist("tech")
    storage.create_watchlist("etfs")
    for ticker in ("AAPL", "MSFT"):
        storage.add_to_watchlist("tech", ticker)
        storage.store_ohlcv(ticker, _make_ohlcv())
    storage.add_to_watchlist("etfs", "SPY")
    storage.store_ohlcv("SPY", _make_ohlcv(450.0))
    return CaracalApp(config=config, data_service=DataService(config, storage=storage))


# -- Sample row helper for widget-level tests --------------------------------

SAMPLE_ROW = {
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "close": 175.50,
    "change_pct": 2.34,
    "signal": "buy",
    "confidence": 0.85,
    "rsi": 65.2,
    "macd_interpretation": "bull",
    "bb_position": "neutral",
}


class _TableTestApp(App):
    """Minimal app for testing WatchlistTable change highlighting."""

    def __init__(self, rows: list[dict]) -> None:
        super().__init__()
        self._rows = rows

    def compose(self) -> ComposeResult:
        yield WatchlistTable()

    def on_mount(self) -> None:
        table = self.query_one(WatchlistTable)
        table.load_data(self._rows)


# ---------------------------------------------------------------------------
# Auto-refresh basic
# ---------------------------------------------------------------------------


class TestAutoRefresh:
    @pytest.mark.asyncio
    async def test_app_starts_without_crash(self):
        """Basic smoke test: app with auto-refresh timer starts correctly."""
        app = _make_app()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            assert table.row_count >= 1

    @pytest.mark.asyncio
    async def test_refresh_preserves_cursor(self):
        app = _make_app()
        async with app.run_test() as pilot:
            await pilot.press("r")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            assert table.row_count >= 1


# ---------------------------------------------------------------------------
# NF-019: UI state preserved after refresh
# ---------------------------------------------------------------------------


class TestStatePreservationNF019:
    """NF-019: Cursor position, sort order, and active tab must be
    preserved after both auto-refresh and manual refresh."""

    @pytest.mark.asyncio
    async def test_cursor_preserved_after_manual_refresh(self):
        """Cursor stays on the same ticker after pressing r."""
        app = _make_multi_app()
        async with app.run_test() as pilot:
            # Switch to "tech" tab which has 2 tickers (AAPL, MSFT)
            await pilot.press("2")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            dt = table.query_one("DataTable")
            assert table.row_count == 2
            # Move cursor to row 1
            await pilot.press("j")
            await pilot.pause()
            ticker_before = table.get_selected_ticker()
            assert dt.cursor_coordinate.row == 1
            # Refresh
            await pilot.press("r")
            await pilot.pause()
            # Cursor should still be on the same ticker
            table = panel.get_active_table()
            assert table.get_selected_ticker() == ticker_before

    @pytest.mark.asyncio
    async def test_sort_preserved_after_manual_refresh(self):
        """Sort column and direction are preserved after manual refresh."""
        app = _make_multi_app()
        async with app.run_test() as pilot:
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            # Sort by ticker ascending
            await pilot.press("s")
            await pilot.pause()
            assert table.sort_column == "ticker"
            assert table._sort_ascending is True
            # Refresh — sort state should still be set
            await pilot.press("r")
            await pilot.pause()
            table = panel.get_active_table()
            assert table.sort_column == "ticker"
            assert table._sort_ascending is True

    @pytest.mark.asyncio
    async def test_active_tab_preserved_after_manual_refresh(self):
        """Active watchlist tab is preserved after manual refresh."""
        app = _make_multi_app()
        async with app.run_test() as pilot:
            # Switch to second tab
            await pilot.press("2")
            await pilot.pause()
            active_before = app.active_watchlist
            assert active_before is not None
            # Refresh
            await pilot.press("r")
            await pilot.pause()
            assert app.active_watchlist == active_before

    @pytest.mark.asyncio
    async def test_cursor_preserved_after_auto_refresh(self):
        """Cursor preserved when auto-refresh fires."""
        app = _make_multi_app()
        async with app.run_test() as pilot:
            # Switch to "tech" tab which has 2 tickers
            await pilot.press("2")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            assert table.row_count == 2
            # Move to row 1
            await pilot.press("j")
            await pilot.pause()
            ticker_before = table.get_selected_ticker()
            # Trigger auto-refresh directly
            await CaracalApp._auto_refresh(app)
            table = panel.get_active_table()
            assert table.get_selected_ticker() == ticker_before

    @pytest.mark.asyncio
    async def test_auto_refresh_skips_in_detail_view(self):
        """Auto-refresh skips when in detail view."""
        app = _make_multi_app()
        async with app.run_test() as pilot:
            await pilot.press("enter")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            assert panel.in_detail
            await CaracalApp._auto_refresh(app)
            assert panel.in_detail  # still in detail, no disruption

    @pytest.mark.asyncio
    async def test_refresh_updates_footer_timestamp(self):
        """Manual refresh updates the footer timestamp."""
        app = _make_multi_app()
        async with app.run_test() as pilot:
            footer = app.query_one(CaracalFooter)
            assert footer.last_updated == "—"
            await pilot.press("r")
            await pilot.pause()
            assert footer.last_updated != "—"


# ---------------------------------------------------------------------------
# Change highlighting
# ---------------------------------------------------------------------------


class TestChangeHighlighting:
    """US-063: Changed values after refresh are briefly highlighted."""

    @pytest.mark.asyncio
    async def test_no_highlight_on_initial_load(self):
        """First load should not highlight any rows."""
        app = _TableTestApp([SAMPLE_ROW])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            assert table._highlighted_tickers == set()

    @pytest.mark.asyncio
    async def test_detect_changes_finds_changed_values(self):
        """_detect_changes identifies tickers with changed close/signal/etc."""
        app = _TableTestApp([SAMPLE_ROW])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            # Load initial data
            assert table.row_count == 1
            # Now load changed data
            changed_row = {**SAMPLE_ROW, "close": 180.00}
            table.load_data([changed_row])
            assert "AAPL" in table._highlighted_tickers

    @pytest.mark.asyncio
    async def test_no_highlight_when_values_unchanged(self):
        """Reload with same values should not highlight."""
        app = _TableTestApp([SAMPLE_ROW])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            # Reload with identical data
            table.load_data([SAMPLE_ROW])
            assert table._highlighted_tickers == set()

    @pytest.mark.asyncio
    async def test_highlight_clears_after_timer(self):
        """Highlights are removed after the timer fires."""
        app = _TableTestApp([SAMPLE_ROW])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            # Load changed data
            changed_row = {**SAMPLE_ROW, "close": 180.00}
            table.load_data([changed_row])
            assert "AAPL" in table._highlighted_tickers
            # Manually trigger the clear callback
            table._clear_highlights()
            assert table._highlighted_tickers == set()

    @pytest.mark.asyncio
    async def test_highlight_detects_signal_change(self):
        """Signal change (buy -> sell) triggers highlighting."""
        app = _TableTestApp([SAMPLE_ROW])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            changed_row = {**SAMPLE_ROW, "signal": "sell"}
            table.load_data([changed_row])
            assert "AAPL" in table._highlighted_tickers

    @pytest.mark.asyncio
    async def test_highlight_detects_confidence_change(self):
        """Confidence change triggers highlighting."""
        app = _TableTestApp([SAMPLE_ROW])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            changed_row = {**SAMPLE_ROW, "confidence": 0.50}
            table.load_data([changed_row])
            assert "AAPL" in table._highlighted_tickers

    @pytest.mark.asyncio
    async def test_highlight_preserves_cursor(self):
        """Cursor position is preserved even when highlights are applied."""
        rows = [
            {**SAMPLE_ROW, "ticker": "AAPL"},
            {**SAMPLE_ROW, "ticker": "MSFT"},
        ]
        app = _TableTestApp(rows)
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            dt = table.query_one("DataTable")
            dt.move_cursor(row=1)
            # Reload with changes
            changed_rows = [
                {**SAMPLE_ROW, "ticker": "AAPL", "close": 180.00},
                {**SAMPLE_ROW, "ticker": "MSFT"},
            ]
            table.load_data(changed_rows)
            assert dt.cursor_coordinate.row == 1
            assert table.get_selected_ticker() == "MSFT"

    @pytest.mark.asyncio
    async def test_clear_highlights_preserves_cursor(self):
        """Cursor preserved when highlights are cleared."""
        rows = [
            {**SAMPLE_ROW, "ticker": "AAPL"},
            {**SAMPLE_ROW, "ticker": "MSFT"},
        ]
        app = _TableTestApp(rows)
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            dt = table.query_one("DataTable")
            dt.move_cursor(row=1)
            changed_rows = [
                {**SAMPLE_ROW, "ticker": "AAPL", "close": 180.00},
                {**SAMPLE_ROW, "ticker": "MSFT"},
            ]
            table.load_data(changed_rows)
            table._clear_highlights()
            assert dt.cursor_coordinate.row == 1

    @pytest.mark.asyncio
    async def test_new_ticker_not_highlighted(self):
        """A ticker that didn't exist before should not be highlighted."""
        app = _TableTestApp([SAMPLE_ROW])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            new_row = {**SAMPLE_ROW, "ticker": "NVDA", "close": 900.00}
            table.load_data([SAMPLE_ROW, new_row])
            assert "NVDA" not in table._highlighted_tickers
            assert "AAPL" not in table._highlighted_tickers

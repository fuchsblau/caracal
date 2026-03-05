"""Tests for WatchlistTable widget."""

import pytest
from rich.text import Text
from textual.app import App, ComposeResult

from caracal.tui.widgets.watchlist_table import WatchlistTable


class WatchlistTableApp(App):
    """Minimal app for testing WatchlistTable."""

    def __init__(self, rows: list[dict]) -> None:
        super().__init__()
        self._rows = rows

    def compose(self) -> ComposeResult:
        yield WatchlistTable()

    def on_mount(self) -> None:
        table = self.query_one(WatchlistTable)
        table.load_data(self._rows)


SAMPLE_ROW = {
    "ticker": "AAPL",
    "close": 175.50,
    "change_pct": 2.34,
    "signal": "buy",
    "confidence": 0.85,
    "rsi": 65.2,
    "macd_interpretation": "bull",
    "bb_position": "neutral",
}


class TestWatchlistTableColumns:
    @pytest.mark.asyncio
    async def test_has_eight_columns(self):
        app = WatchlistTableApp([SAMPLE_ROW])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            assert table.column_count == 8

    @pytest.mark.asyncio
    async def test_renders_ticker(self):
        app = WatchlistTableApp([SAMPLE_ROW])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            assert table.row_count == 1


class TestWatchlistTableFormatting:
    @pytest.mark.asyncio
    async def test_positive_change_is_green(self):
        app = WatchlistTableApp([SAMPLE_ROW])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            from textual.widgets import DataTable
            dt = table.query_one(DataTable)
            from textual.coordinate import Coordinate
            cell = dt.get_cell_at(Coordinate(0, 2))  # Change% column
            assert isinstance(cell, Text)
            assert "#4caf50" in str(cell.style) or "4caf50" in str(cell.style).lower()

    @pytest.mark.asyncio
    async def test_negative_change_is_red(self):
        row = {**SAMPLE_ROW, "change_pct": -1.5}
        app = WatchlistTableApp([row])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            dt = table.query_one("DataTable")
            from textual.coordinate import Coordinate
            cell = dt.get_cell_at(Coordinate(0, 2))
            assert isinstance(cell, Text)
            assert "#f44336" in str(cell.style) or "f44336" in str(cell.style).lower()


class TestWatchlistTableNullHandling:
    @pytest.mark.asyncio
    async def test_handles_null_values(self):
        row = {
            "ticker": "NEW",
            "close": None,
            "change_pct": None,
            "signal": "N/A",
            "confidence": None,
            "rsi": None,
            "macd_interpretation": None,
            "bb_position": None,
        }
        app = WatchlistTableApp([row])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            assert table.row_count == 1


class TestWatchlistTableSorting:
    @pytest.mark.asyncio
    async def test_cycle_sort_changes_order(self):
        rows = [
            {**SAMPLE_ROW, "ticker": "AAPL", "change_pct": 2.0},
            {**SAMPLE_ROW, "ticker": "MSFT", "change_pct": -1.0},
        ]
        app = WatchlistTableApp(rows)
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            # First sort: ticker ascending
            table.cycle_sort()
            assert table.sort_column == "ticker"
            assert table._sort_ascending is True

            # Second sort: ticker descending
            table.cycle_sort()
            assert table.sort_column == "ticker"
            assert table._sort_ascending is False

            # Third sort: change_pct ascending
            table.cycle_sort()
            assert table.sort_column == "change_pct"
            assert table._sort_ascending is True

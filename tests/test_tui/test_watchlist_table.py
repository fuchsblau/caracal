"""Tests for WatchlistTable widget."""

import pytest
from rich.text import Text
from textual.app import App, ComposeResult
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Static

from caracal.tui.theme import (
    COLOR_MUTED,
    COLOR_NEGATIVE,
    COLOR_NEUTRAL,
    COLOR_OVERBOUGHT,
    COLOR_OVERSOLD,
    COLOR_POSITIVE,
    COLOR_PRICE,
    SIGNAL_COLORS,
)
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
    "name": "Apple Inc.",
    "close": 175.50,
    "change_pct": 2.34,
    "signal": "buy",
    "confidence": 0.85,
    "rsi": 65.2,
    "macd_interpretation": "bull",
    "bb_position": "neutral",
}

NULL_ROW = {
    "ticker": "NEW",
    "name": "NEW",
    "close": None,
    "change_pct": None,
    "signal": "N/A",
    "confidence": None,
    "rsi": None,
    "macd_interpretation": None,
    "bb_position": None,
}

# Column indices for readability
COL_TICKER = 0
COL_NAME = 1
COL_PRICE = 2
COL_CHANGE = 3
COL_SIGNAL = 4
COL_CONFIDENCE = 5
COL_RSI = 6
COL_MACD = 7
COL_BB = 8


def _get_cell(dt: DataTable, row: int, col: int) -> Text:
    """Retrieve a cell from the DataTable and assert it is Rich Text."""
    cell = dt.get_cell_at(Coordinate(row, col))
    assert isinstance(cell, Text), f"Expected Text at ({row},{col}), got {type(cell)}"
    return cell


def _style_contains(cell: Text, color: str) -> bool:
    """Check whether a cell's style string contains the given color hex."""
    style_str = str(cell.style).lower()
    return color.lower().lstrip("#") in style_str


class TestWatchlistTableColumns:
    """Verify all 9 columns are present with correct headers."""

    @pytest.mark.asyncio
    async def test_has_nine_columns(self):
        app = WatchlistTableApp([SAMPLE_ROW])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            assert table.column_count == 9

    @pytest.mark.asyncio
    async def test_column_headers(self):
        """Verify column header labels match US-060 spec."""
        app = WatchlistTableApp([SAMPLE_ROW])
        async with app.run_test():
            wt = app.query_one(WatchlistTable)
            dt = wt.query_one(DataTable)
            headers = [col.label.plain for col in dt.columns.values()]
            assert headers == [
                "Ticker", "Name", "Price", "Chg%",
                "Signal", "Conf", "RSI", "MACD", "BB",
            ]

    @pytest.mark.asyncio
    async def test_renders_one_row(self):
        app = WatchlistTableApp([SAMPLE_ROW])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_renders_multiple_rows(self):
        rows = [
            {**SAMPLE_ROW, "ticker": "AAPL"},
            {**SAMPLE_ROW, "ticker": "MSFT"},
            {**SAMPLE_ROW, "ticker": "GOOGL"},
        ]
        app = WatchlistTableApp(rows)
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            assert table.row_count == 3


class TestWatchlistTableTickerColumn:
    """US-060: Ticker column is bold."""

    @pytest.mark.asyncio
    async def test_ticker_text_content(self):
        app = WatchlistTableApp([SAMPLE_ROW])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_TICKER)
            assert cell.plain == "AAPL"

    @pytest.mark.asyncio
    async def test_ticker_is_bold(self):
        app = WatchlistTableApp([SAMPLE_ROW])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_TICKER)
            assert "bold" in str(cell.style)


class TestWatchlistTableNameColumn:
    """US-060: Name column shows company name in muted style."""

    @pytest.mark.asyncio
    async def test_name_text_content(self):
        app = WatchlistTableApp([SAMPLE_ROW])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_NAME)
            assert cell.plain == "Apple Inc."

    @pytest.mark.asyncio
    async def test_name_falls_back_to_ticker(self):
        row = {**SAMPLE_ROW}
        del row["name"]
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_NAME)
            assert cell.plain == "AAPL"


class TestWatchlistTablePriceColumn:
    """US-060: Price column with 2 decimal formatting."""

    @pytest.mark.asyncio
    async def test_price_formatted_two_decimals(self):
        app = WatchlistTableApp([SAMPLE_ROW])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_PRICE)
            assert cell.plain == "175.50"

    @pytest.mark.asyncio
    async def test_price_color(self):
        app = WatchlistTableApp([SAMPLE_ROW])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_PRICE)
            assert _style_contains(cell, COLOR_PRICE)

    @pytest.mark.asyncio
    async def test_price_none_shows_na(self):
        app = WatchlistTableApp([NULL_ROW])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_PRICE)
            assert cell.plain == "N/A"


class TestWatchlistTableChangeColumn:
    """US-060: Change% with green/red color coding."""

    @pytest.mark.asyncio
    async def test_positive_change_is_green(self):
        app = WatchlistTableApp([SAMPLE_ROW])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_CHANGE)
            assert cell.plain == "+2.34%"
            assert _style_contains(cell, COLOR_POSITIVE)

    @pytest.mark.asyncio
    async def test_negative_change_is_red(self):
        row = {**SAMPLE_ROW, "change_pct": -1.50}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_CHANGE)
            assert cell.plain == "-1.50%"
            assert _style_contains(cell, COLOR_NEGATIVE)

    @pytest.mark.asyncio
    async def test_zero_change_is_green(self):
        row = {**SAMPLE_ROW, "change_pct": 0.0}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_CHANGE)
            assert cell.plain == "+0.00%"
            assert _style_contains(cell, COLOR_POSITIVE)

    @pytest.mark.asyncio
    async def test_change_none_shows_na(self):
        app = WatchlistTableApp([NULL_ROW])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_CHANGE)
            assert cell.plain == "N/A"


class TestWatchlistTableSignalColumn:
    """US-060: Signal column with BUY/SELL/HOLD color coding."""

    @pytest.mark.asyncio
    async def test_buy_signal_green(self):
        row = {**SAMPLE_ROW, "signal": "buy"}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_SIGNAL)
            assert cell.plain == "BUY"
            assert _style_contains(cell, SIGNAL_COLORS["buy"])
            assert "bold" in str(cell.style)

    @pytest.mark.asyncio
    async def test_sell_signal_red(self):
        row = {**SAMPLE_ROW, "signal": "sell"}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_SIGNAL)
            assert cell.plain == "SELL"
            assert _style_contains(cell, SIGNAL_COLORS["sell"])
            assert "bold" in str(cell.style)

    @pytest.mark.asyncio
    async def test_hold_signal_yellow(self):
        row = {**SAMPLE_ROW, "signal": "hold"}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_SIGNAL)
            assert cell.plain == "HOLD"
            assert _style_contains(cell, SIGNAL_COLORS["hold"])
            assert "bold" in str(cell.style)

    @pytest.mark.asyncio
    async def test_na_signal(self):
        row = {**SAMPLE_ROW, "signal": "N/A"}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_SIGNAL)
            assert cell.plain == "N/A"


class TestWatchlistTableConfidenceColumn:
    """US-060: Confidence % with brightness gradient."""

    @pytest.mark.asyncio
    async def test_high_confidence_bold_green(self):
        row = {**SAMPLE_ROW, "confidence": 0.85}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_CONFIDENCE)
            assert cell.plain == "85%"
            assert _style_contains(cell, COLOR_POSITIVE)
            assert "bold" in str(cell.style)

    @pytest.mark.asyncio
    async def test_medium_confidence_neutral(self):
        row = {**SAMPLE_ROW, "confidence": 0.55}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_CONFIDENCE)
            assert cell.plain == "55%"
            assert _style_contains(cell, COLOR_NEUTRAL)

    @pytest.mark.asyncio
    async def test_low_confidence_muted(self):
        row = {**SAMPLE_ROW, "confidence": 0.15}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_CONFIDENCE)
            assert cell.plain == "15%"
            assert "dim" in str(cell.style)

    @pytest.mark.asyncio
    async def test_confidence_none_shows_na(self):
        app = WatchlistTableApp([NULL_ROW])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_CONFIDENCE)
            assert cell.plain == "N/A"


class TestWatchlistTableRSIColumn:
    """US-060: RSI 14 interpreted with arrow symbols."""

    @pytest.mark.asyncio
    async def test_rsi_neutral_with_dash(self):
        row = {**SAMPLE_ROW, "rsi": 50.3}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_RSI)
            assert "50" in cell.plain
            assert "\u2014" in cell.plain  # em dash

    @pytest.mark.asyncio
    async def test_rsi_overbought_with_up_arrow(self):
        row = {**SAMPLE_ROW, "rsi": 72.4}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_RSI)
            assert "72" in cell.plain
            assert "\u25b2" in cell.plain  # up arrow
            assert _style_contains(cell, COLOR_OVERBOUGHT)

    @pytest.mark.asyncio
    async def test_rsi_oversold_with_down_arrow(self):
        row = {**SAMPLE_ROW, "rsi": 22.8}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_RSI)
            assert "23" in cell.plain
            assert "\u25bc" in cell.plain  # down arrow
            assert _style_contains(cell, COLOR_OVERSOLD)

    @pytest.mark.asyncio
    async def test_rsi_none_shows_na(self):
        app = WatchlistTableApp([NULL_ROW])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_RSI)
            assert cell.plain == "N/A"


class TestWatchlistTableMACDColumn:
    """US-060: MACD with bull/bear symbol."""

    @pytest.mark.asyncio
    async def test_macd_bull_green(self):
        row = {**SAMPLE_ROW, "macd_interpretation": "bull"}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_MACD)
            assert "\u25b2" in cell.plain
            assert "bull" in cell.plain
            assert _style_contains(cell, COLOR_POSITIVE)
            assert "bold" in str(cell.style)

    @pytest.mark.asyncio
    async def test_macd_bear_red(self):
        row = {**SAMPLE_ROW, "macd_interpretation": "bear"}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_MACD)
            assert "\u25bc" in cell.plain
            assert "bear" in cell.plain
            assert _style_contains(cell, COLOR_NEGATIVE)
            assert "bold" in str(cell.style)

    @pytest.mark.asyncio
    async def test_macd_none_shows_na(self):
        app = WatchlistTableApp([NULL_ROW])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_MACD)
            assert cell.plain == "N/A"


class TestWatchlistTableBBColumn:
    """US-060: Bollinger Band position (OB/OS/OK)."""

    @pytest.mark.asyncio
    async def test_bb_overbought(self):
        row = {**SAMPLE_ROW, "bb_position": "overbought"}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_BB)
            assert "OB" in cell.plain
            assert "\u25b2" in cell.plain
            assert _style_contains(cell, COLOR_OVERBOUGHT)

    @pytest.mark.asyncio
    async def test_bb_oversold(self):
        row = {**SAMPLE_ROW, "bb_position": "oversold"}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_BB)
            assert "OS" in cell.plain
            assert "\u25bc" in cell.plain
            assert _style_contains(cell, COLOR_OVERSOLD)

    @pytest.mark.asyncio
    async def test_bb_neutral(self):
        row = {**SAMPLE_ROW, "bb_position": "neutral"}
        app = WatchlistTableApp([row])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_BB)
            assert "OK" in cell.plain
            assert "\u2014" in cell.plain
            assert _style_contains(cell, COLOR_NEUTRAL)

    @pytest.mark.asyncio
    async def test_bb_none_shows_na(self):
        app = WatchlistTableApp([NULL_ROW])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            cell = _get_cell(dt, 0, COL_BB)
            assert cell.plain == "N/A"


class TestWatchlistTableNullHandling:
    """Verify all columns handle None values gracefully."""

    @pytest.mark.asyncio
    async def test_handles_all_null_values(self):
        app = WatchlistTableApp([NULL_ROW])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_null_row_all_cells_are_text(self):
        """Every cell in a null row must be a Rich Text object."""
        app = WatchlistTableApp([NULL_ROW])
        async with app.run_test():
            dt = app.query_one(WatchlistTable).query_one(DataTable)
            for col in range(9):
                cell = dt.get_cell_at(Coordinate(0, col))
                assert isinstance(cell, Text), f"Column {col} is not Text"


class TestWatchlistTableEmptyHint:
    @pytest.mark.asyncio
    async def test_empty_table_shows_hint(self):
        app = WatchlistTableApp([])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            hint = table.query_one("#empty-hint", Static)
            assert hint.display is True
            dt = table.query_one(DataTable)
            assert dt.display is False

    @pytest.mark.asyncio
    async def test_populated_table_hides_hint(self):
        app = WatchlistTableApp([SAMPLE_ROW])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            hint = table.query_one("#empty-hint", Static)
            assert hint.display is False
            dt = table.query_one(DataTable)
            assert dt.display is True


class TestWatchlistTableCursorMessages:
    """US-064: WatchlistTable emits CursorChanged and RowActivated messages."""

    @pytest.mark.asyncio
    async def test_cursor_changed_message_has_ticker(self):
        """CursorChanged message carries the ticker string."""
        msg = WatchlistTable.CursorChanged("AAPL")
        assert msg.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_cursor_changed_message_accepts_none(self):
        """CursorChanged accepts None for empty tables."""
        msg = WatchlistTable.CursorChanged(None)
        assert msg.ticker is None

    @pytest.mark.asyncio
    async def test_row_activated_message_has_ticker(self):
        """RowActivated message carries the ticker string."""
        msg = WatchlistTable.RowActivated("MSFT")
        assert msg.ticker == "MSFT"

    @pytest.mark.asyncio
    async def test_get_selected_ticker_returns_current_cursor(self):
        """get_selected_ticker returns the ticker at the cursor position."""
        rows = [
            {**SAMPLE_ROW, "ticker": "AAPL"},
            {**SAMPLE_ROW, "ticker": "MSFT"},
        ]
        app = WatchlistTableApp(rows)
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            # Cursor at row 0
            ticker = table.get_selected_ticker()
            assert ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_get_selected_ticker_none_on_empty_table(self):
        """get_selected_ticker returns None when table is empty."""
        app = WatchlistTableApp([])
        async with app.run_test():
            table = app.query_one(WatchlistTable)
            assert table.get_selected_ticker() is None


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

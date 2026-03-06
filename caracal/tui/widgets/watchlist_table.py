"""WatchlistTable -- DataTable widget for a single watchlist."""

from __future__ import annotations

from rich.text import Text
from textual.message import Message
from textual.widget import Widget
from textual.widgets import DataTable, Static

from caracal.tui.theme import (
    COLOR_HIGHLIGHT,
    COLOR_MUTED,
    COLOR_NEGATIVE,
    COLOR_POSITIVE,
    COLOR_PRICE,
    SIGNAL_COLORS,
    format_bb,
    format_confidence,
    format_macd,
    format_rsi,
)

# Sort cycle: column index and key name
_SORT_COLUMNS = [
    (0, "ticker"),
    (2, "change_pct"),
    (3, "signal"),
    (4, "confidence"),
]


class WatchlistTable(Widget):
    """Watchlist table with indicator columns and sorting."""

    class CursorChanged(Message):
        """Emitted when the selected ticker changes."""

        def __init__(self, ticker: str | None) -> None:
            super().__init__()
            self.ticker = ticker

    class RowActivated(Message):
        """Emitted when a row is selected via Enter."""

        def __init__(self, ticker: str) -> None:
            super().__init__()
            self.ticker = ticker

    # Keys compared to detect change-worthy differences
    _CHANGE_KEYS = ("close", "change_pct", "signal", "confidence")

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._rows: list[dict] = []
        self._sort_cycle_index: int = -1
        self._sort_ascending: bool = True
        self._previous_values: dict[str, dict] = {}
        self._highlighted_tickers: set[str] = set()
        self._highlight_timer = None

    @property
    def sort_column(self) -> str | None:
        """Return the name of the current sort column, or None."""
        if self._sort_cycle_index < 0:
            return None
        return _SORT_COLUMNS[self._sort_cycle_index][1]

    @property
    def row_count(self) -> int:
        """Return the number of rows in the underlying DataTable."""
        return self.query_one(DataTable).row_count

    @property
    def column_count(self) -> int:
        """Return the number of columns in the underlying DataTable."""
        return len(self.query_one(DataTable).columns)

    def compose(self):
        """Compose the widget with an inner DataTable."""
        yield DataTable(
            cursor_type="row",
            zebra_stripes=True,
            cursor_foreground_priority="renderable",
        )
        yield Static("No tickers yet — press [bold]a[/] to add", id="empty-hint")

    def on_mount(self) -> None:
        """Set up columns when the widget is mounted."""
        table = self.query_one(DataTable)
        table.add_columns(
            "Ticker", "Name", "Price", "Chg%", "Signal", "Conf", "RSI", "MACD", "BB",
        )
        # Show hint by default (hidden once load_data adds rows)
        table.display = False

    def load_data(self, rows: list[dict]) -> None:
        """Load or refresh watchlist data into the table."""
        table = self.query_one(DataTable)
        hint = self.query_one("#empty-hint", Static)

        # Save cursor position
        cursor_ticker = self._get_cursor_ticker()

        # Store previous values for change detection
        self._previous_values = {r["ticker"]: r for r in self._rows}

        # Detect which tickers have changed values
        self._highlighted_tickers = self._detect_changes(rows)

        self._rows = rows

        table.clear()
        for row in rows:
            highlight = row["ticker"] in self._highlighted_tickers
            table.add_row(*self._format_row(row, highlight=highlight), key=row["ticker"])

        # Toggle empty hint vs table
        table.display = len(rows) > 0
        hint.display = len(rows) == 0

        # Restore cursor position
        if cursor_ticker:
            self._restore_cursor(cursor_ticker)

        # Schedule highlight removal after 1.5 seconds
        if self._highlighted_tickers:
            if self._highlight_timer is not None:
                self._highlight_timer.stop()
            self._highlight_timer = self.set_timer(1.5, self._clear_highlights)

    def _detect_changes(self, new_rows: list[dict]) -> set[str]:
        """Compare new rows with previous values and return changed tickers."""
        if not self._previous_values:
            return set()
        changed = set()
        for row in new_rows:
            ticker = row["ticker"]
            prev = self._previous_values.get(ticker)
            if prev is None:
                continue
            for key in self._CHANGE_KEYS:
                if row.get(key) != prev.get(key):
                    changed.add(ticker)
                    break
        return changed

    def _clear_highlights(self) -> None:
        """Remove change highlights by reloading data without highlight flags."""
        self._highlighted_tickers.clear()
        self._highlight_timer = None
        table = self.query_one(DataTable)
        cursor_ticker = self._get_cursor_ticker()
        table.clear()
        for row in self._rows:
            table.add_row(*self._format_row(row, highlight=False), key=row["ticker"])
        if cursor_ticker:
            self._restore_cursor(cursor_ticker)

    def _format_row(self, row: dict, *, highlight: bool = False) -> tuple:
        """Format a data row into Rich Text cells.

        When *highlight* is True, changed rows get a subtle background
        flash that is removed after a short timer.
        """
        bg = f" on {COLOR_HIGHLIGHT}" if highlight else ""

        ticker = Text(row["ticker"], style=f"bold{bg}")
        name = Text(row.get("name", row["ticker"]), style=f"{COLOR_MUTED}{bg}")

        if row["close"] is not None:
            price = Text(f"{row['close']:.2f}", style=f"{COLOR_PRICE}{bg}", justify="right")
        else:
            price = Text("N/A", style=f"{COLOR_MUTED}{bg}", justify="right")

        if row["change_pct"] is not None:
            pct_val = row["change_pct"]
            pct_color = COLOR_POSITIVE if pct_val >= 0 else COLOR_NEGATIVE
            change = Text(f"{pct_val:+.2f}%", style=f"{pct_color}{bg}", justify="right")
        else:
            change = Text("N/A", style=f"{COLOR_MUTED}{bg}", justify="right")

        sig = row["signal"]
        sig_color = SIGNAL_COLORS.get(sig, COLOR_MUTED)
        signal = Text(sig.upper(), style=f"bold {sig_color}{bg}", justify="right")

        confidence = format_confidence(row.get("confidence"))
        rsi = format_rsi(row.get("rsi"))
        macd = format_macd(row.get("macd_interpretation"))
        bb = format_bb(row.get("bb_position"))

        return ticker, name, price, change, signal, confidence, rsi, macd, bb

    def get_selected_ticker(self) -> str | None:
        """Return the ticker at the current cursor position."""
        return self._get_cursor_ticker()

    def _get_cursor_ticker(self) -> str | None:
        """Get the ticker string at the current cursor row."""
        table = self.query_one(DataTable)
        if table.row_count == 0:
            return None
        try:
            row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
            return str(row_key.value)
        except Exception:
            return None

    def _restore_cursor(self, ticker: str) -> None:
        """Restore the cursor to the row matching the given ticker."""
        table = self.query_one(DataTable)
        for idx, row_key in enumerate(table.rows):
            if str(row_key.value) == ticker:
                table.move_cursor(row=idx)
                return

    def cycle_sort(self) -> None:
        """Cycle through sort columns or toggle direction."""
        if self._sort_cycle_index < 0:
            # First sort: start with first column ascending
            self._sort_cycle_index = 0
            self._sort_ascending = True
        elif self._sort_ascending:
            # Currently ascending → toggle to descending (same column)
            self._sort_ascending = False
        else:
            # Currently descending → move to next column ascending
            self._sort_cycle_index = (self._sort_cycle_index + 1) % len(_SORT_COLUMNS)
            self._sort_ascending = True
        self._apply_sort()

    def _apply_sort(self) -> None:
        """Sort the rows by the current sort column and reload."""
        if self._sort_cycle_index < 0 or not self._rows:
            return
        _, key = _SORT_COLUMNS[self._sort_cycle_index]
        self._rows.sort(
            key=lambda r: (r.get(key) is None, r.get(key, "")),
            reverse=not self._sort_ascending,
        )
        self.load_data(self._rows)

    def on_data_table_cursor_moved(self, event) -> None:
        """Forward cursor moves as CursorChanged messages."""
        ticker = self._get_cursor_ticker()
        self.post_message(self.CursorChanged(ticker))

    def on_data_table_row_selected(self, event) -> None:
        """Forward Enter/row-select as RowActivated message."""
        ticker = self._get_cursor_ticker()
        if ticker:
            self.post_message(self.RowActivated(ticker))

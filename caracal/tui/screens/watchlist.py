"""Watchlist screen — default screen showing all tickers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from caracal.storage.duckdb import StorageError

if TYPE_CHECKING:
    from caracal.tui.data import DataService


class WatchlistScreen(Screen):
    """Main screen showing watchlist overview in a DataTable."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "select_row", "Detail"),
        Binding("r", "refresh_data", "Refresh"),
        Binding("c", "create_watchlist", "Create"),
        Binding("d", "delete_watchlist", "Delete"),
        Binding("w", "select_watchlist", "Watchlists"),
    ]

    def __init__(self, data_service: DataService) -> None:
        super().__init__()
        self.data_service = data_service
        self._watchlist_names: list[str] = []
        self._current_index: int = 0

    @property
    def current_watchlist(self) -> str | None:
        if not self._watchlist_names:
            return None
        return self._watchlist_names[self._current_index]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="watchlist-table", cursor_type="row", zebra_stripes=True)
        yield Static(id="empty-hint")
        yield Footer()

    def on_mount(self) -> None:
        self._watchlist_names = self.data_service.get_watchlist_names()
        table = self.query_one("#watchlist-table", DataTable)
        table.add_columns("Symbol", "Price", "Change%", "Signal")

        if not self._watchlist_names:
            table.display = False
            self.query_one("#empty-hint", Static).update(
                "No watchlists found. Press c to create one."
            )
            return

        self._load_watchlist()

    def _load_watchlist(self) -> None:
        name = self.current_watchlist
        if name is None:
            return

        total = len(self._watchlist_names)
        idx = self._current_index + 1
        self.sub_title = f"{name} ({idx}/{total})"
        table = self.query_one("#watchlist-table", DataTable)
        table.clear()
        hint = self.query_one("#empty-hint", Static)

        rows = self.data_service.get_watchlist_overview(name)
        if not rows:
            table.display = False
            msg = f"No tickers in '{name}'."
            msg += f" Add with: caracal watchlist add {name} <ticker>"
            hint.update(msg)
            hint.display = True
            return

        table.display = True
        hint.display = False

        for row in rows:
            close_str = f"{row['close']:.2f}" if row["close"] is not None else "N/A"
            pct_str = (
                f"{row['change_pct']:+.2f}%"
                if row["change_pct"] is not None
                else "N/A"
            )
            signal = row["signal"]
            table.add_row(row["ticker"], close_str, pct_str, signal, key=row["ticker"])

    def action_cursor_down(self) -> None:
        self.query_one("#watchlist-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#watchlist-table", DataTable).action_cursor_up()

    def action_select_row(self) -> None:
        table = self.query_one("#watchlist-table", DataTable)
        if table.row_count == 0:
            return
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        ticker = str(row_key.value)
        from caracal.tui.screens.stock_detail import StockDetailScreen

        self.app.push_screen(StockDetailScreen(ticker, self.data_service))

    def action_create_watchlist(self) -> None:
        from caracal.tui.screens.create_watchlist import CreateWatchlistModal

        self.app.push_screen(CreateWatchlistModal(), self._on_create_result)

    def _on_create_result(self, name: str | None) -> None:
        if name is None:
            return
        try:
            self.data_service.create_watchlist(name)
        except StorageError as e:
            self.notify(str(e), severity="error")
            return
        self._watchlist_names = self.data_service.get_watchlist_names()
        self._current_index = self._watchlist_names.index(name)
        self._load_watchlist()

    def action_delete_watchlist(self) -> None:
        if not self._watchlist_names:
            return
        name = self.current_watchlist
        from caracal.tui.screens.delete_watchlist import DeleteWatchlistModal

        self.app.push_screen(DeleteWatchlistModal(name), self._on_delete_result)

    def _on_delete_result(self, confirmed: bool) -> None:
        if not confirmed:
            return
        name = self.current_watchlist
        self.data_service.delete_watchlist(name)
        self._watchlist_names = self.data_service.get_watchlist_names()
        if self._watchlist_names:
            self._current_index = min(
                self._current_index, len(self._watchlist_names) - 1
            )
            self._load_watchlist()
        else:
            self._current_index = 0
            self._show_empty_state()

    def action_select_watchlist(self) -> None:
        if not self._watchlist_names:
            return
        watchlists = self.data_service.get_watchlists()
        current = self.current_watchlist
        from caracal.tui.screens.watchlist_selector import WatchlistSelectorModal

        self.app.push_screen(
            WatchlistSelectorModal(watchlists, current), self._on_select_result
        )

    def _on_select_result(self, name: str | None) -> None:
        if name is None:
            return
        self._current_index = self._watchlist_names.index(name)
        self._load_watchlist()

    def _show_empty_state(self) -> None:
        self.sub_title = ""
        table = self.query_one("#watchlist-table", DataTable)
        table.clear()
        table.display = False
        hint = self.query_one("#empty-hint", Static)
        hint.update("No watchlists found. Press c to create one.")
        hint.display = True

    def action_refresh_data(self) -> None:
        """Reload data from DuckDB cache."""
        self._load_watchlist()
        self.notify("Data refreshed from cache", severity="information")

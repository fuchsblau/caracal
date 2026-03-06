"""Caracal TUI — interactive terminal interface."""

from __future__ import annotations

from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive
from caracal.tui.widgets.header import CaracalHeader

from caracal.config import CaracalConfig
from caracal.tui.data import DataService
from caracal.tui.widgets.footer import CaracalFooter
from caracal.tui.widgets.side_panel import SidePanel
from caracal.tui.widgets.watchlist_panel import WatchlistPanel


class CaracalApp(App):
    """Caracal interactive terminal interface."""

    CSS_PATH = "styles/app.tcss"
    TITLE = "Caracal"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=False),
        Binding("i", "show_info", "Info", show=False),
        Binding("enter", "drill_down", "Detail", show=False),
        Binding("escape", "back", "Back", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("s", "cycle_sort", "Sort"),
        Binding("r", "refresh_live", "Refresh"),
        Binding("c", "create_watchlist", "+List"),
        Binding("d", "delete_watchlist", "-List"),
        Binding("a", "add_ticker", "+Ticker"),
        Binding("x", "remove_ticker", "-Ticker"),
        Binding("1", "switch_tab('1')", "Tab 1", show=False),
        Binding("2", "switch_tab('2')", "Tab 2", show=False),
        Binding("3", "switch_tab('3')", "Tab 3", show=False),
        Binding("4", "switch_tab('4')", "Tab 4", show=False),
        Binding("5", "switch_tab('5')", "Tab 5", show=False),
        Binding("6", "switch_tab('6')", "Tab 6", show=False),
        Binding("7", "switch_tab('7')", "Tab 7", show=False),
        Binding("8", "switch_tab('8')", "Tab 8", show=False),
        Binding("9", "switch_tab('9')", "Tab 9", show=False),
    ]

    focused_asset: reactive[str | None] = reactive(None)
    active_watchlist: reactive[str | None] = reactive(None)

    def __init__(
        self,
        config: CaracalConfig,
        data_service: DataService | None = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.data_service = data_service or DataService(config)
        self._owns_data_service = data_service is None
        self._watchlist_names: list[str] = []

    def compose(self) -> ComposeResult:
        yield CaracalHeader(show_clock=True, icon="◉")
        with Horizontal(id="main-layout"):
            yield WatchlistPanel(id="watchlist-panel")
            yield SidePanel(id="side-panel")
        yield CaracalFooter()

    async def on_mount(self) -> None:
        self._watchlist_names = self.data_service.get_watchlist_names()
        await self._load_all_watchlists()
        # Start auto-refresh timer (30s)
        self.set_interval(30, self._auto_refresh)

    async def _load_all_watchlists(self) -> None:
        """Load all watchlists into the panel."""
        panel = self.query_one("#watchlist-panel", WatchlistPanel)
        data = {}
        for name in self._watchlist_names:
            data[name] = self.data_service.get_watchlist_overview(name)
        await panel.load_watchlists(data)
        if self._watchlist_names:
            self.active_watchlist = self._watchlist_names[0]
        self._update_footer_from_db()

    def _update_footer_from_db(self) -> None:
        """Set footer timestamp from the latest OHLCV data date in DB."""
        name = self.active_watchlist
        if not name:
            return
        latest = self.data_service.get_latest_data_date(name)
        if latest:
            self.query_one(CaracalFooter).last_updated = latest

    async def _auto_refresh(self) -> None:
        """Auto-refresh from DB cache."""
        name = self.active_watchlist
        if not name:
            return
        panel = self.query_one("#watchlist-panel", WatchlistPanel)
        if panel.in_detail:
            return
        rows = self.data_service.get_watchlist_overview(name)
        panel.refresh_watchlist(name, rows)

    def on_tabbed_content_tab_activated(self, event) -> None:
        """Sync active_watchlist when tabs are switched (arrow keys, clicks)."""
        tab_id = str(event.pane.id or "")
        if tab_id.startswith("tab-"):
            self.active_watchlist = tab_id[4:]

    # -- Navigation -----------------------------------------------------------

    def action_cursor_down(self) -> None:
        panel = self.query_one("#watchlist-panel", WatchlistPanel)
        if panel.in_detail:
            return
        table = panel.get_active_table()
        if table:
            table.query_one("DataTable").action_cursor_down()

    def action_cursor_up(self) -> None:
        panel = self.query_one("#watchlist-panel", WatchlistPanel)
        if panel.in_detail:
            return
        table = panel.get_active_table()
        if table:
            table.query_one("DataTable").action_cursor_up()

    def action_drill_down(self) -> None:
        panel = self.query_one("#watchlist-panel", WatchlistPanel)
        if panel.in_detail:
            return
        table = panel.get_active_table()
        if not table:
            return
        ticker = table.get_selected_ticker()
        if not ticker:
            return
        detail = self.data_service.get_stock_detail(ticker)
        panel.show_detail(detail)
        self.focused_asset = ticker

    def action_back(self) -> None:
        panel = self.query_one("#watchlist-panel", WatchlistPanel)
        if panel.in_detail:
            panel.hide_detail()

    def action_cycle_sort(self) -> None:
        panel = self.query_one("#watchlist-panel", WatchlistPanel)
        if panel.in_detail:
            return
        table = panel.get_active_table()
        if table:
            table.cycle_sort()

    def action_refresh_live(self) -> None:
        """Manual refresh — fetch fresh data from provider."""
        self.run_worker(self._do_live_refresh(), exclusive=True)

    async def _do_live_refresh(self) -> None:
        name = self.active_watchlist
        if not name:
            return
        rows = self.data_service.refresh_watchlist_live(name)
        panel = self.query_one("#watchlist-panel", WatchlistPanel)
        panel.refresh_watchlist(name, rows)
        self.query_one(CaracalFooter).last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def action_switch_tab(self, number: str) -> None:
        idx = int(number) - 1
        if 0 <= idx < len(self._watchlist_names):
            panel = self.query_one("#watchlist-panel", WatchlistPanel)
            if panel.in_detail:
                panel.hide_detail()
            tc = panel.query_one("#watchlist-tabs")
            tab_id = f"tab-{self._watchlist_names[idx]}"
            tc.active = tab_id
            self.active_watchlist = self._watchlist_names[idx]

    # -- CRUD (delegates to modals, same as before) ---------------------------

    def action_create_watchlist(self) -> None:
        from caracal.tui.screens.create_watchlist import CreateWatchlistModal

        self.push_screen(CreateWatchlistModal(), self._on_create_result)

    async def _on_create_result(self, name: str | None) -> None:
        if name is None:
            return
        from caracal.storage.duckdb import StorageError

        try:
            self.data_service.create_watchlist(name)
        except StorageError as e:
            self.notify(str(e), severity="error")
            return
        self._watchlist_names = self.data_service.get_watchlist_names()
        await self._load_all_watchlists()

    def action_delete_watchlist(self) -> None:
        if not self.active_watchlist:
            return
        from caracal.tui.screens.delete_watchlist import DeleteWatchlistModal

        self.push_screen(
            DeleteWatchlistModal(self.active_watchlist), self._on_delete_result
        )

    async def _on_delete_result(self, confirmed: bool) -> None:
        if not confirmed:
            return
        self.data_service.delete_watchlist(self.active_watchlist)
        self._watchlist_names = self.data_service.get_watchlist_names()
        await self._load_all_watchlists()
        if not self._watchlist_names:
            self.active_watchlist = None

    def action_add_ticker(self) -> None:
        if not self.active_watchlist:
            return
        from caracal.tui.screens.add_ticker import AddTickerModal

        self.push_screen(AddTickerModal(), self._on_add_result)

    def _on_add_result(self, tickers: list[str] | None) -> None:
        if tickers is None:
            return
        from caracal.storage.duckdb import StorageError

        try:
            added, duplicates = self.data_service.add_to_watchlist(
                self.active_watchlist, tickers
            )
        except StorageError as e:
            self.notify(str(e), severity="error")
            return
        if duplicates:
            self.notify(
                f"Already in watchlist: {', '.join(duplicates)}", severity="warning"
            )
        if added:
            self._reload_active_watchlist()

    def action_remove_ticker(self) -> None:
        if not self.active_watchlist:
            return
        panel = self.query_one("#watchlist-panel", WatchlistPanel)
        table = panel.get_active_table()
        if not table or table.row_count == 0:
            return
        ticker = table.get_selected_ticker()
        if not ticker:
            return
        from caracal.tui.screens.remove_ticker import RemoveTickerModal

        self._pending_remove_ticker = ticker
        self.push_screen(RemoveTickerModal(ticker), self._on_remove_result)

    def _on_remove_result(self, confirmed: bool) -> None:
        if not confirmed:
            return
        ticker = self._pending_remove_ticker
        if not ticker:
            return
        from caracal.storage.duckdb import StorageError

        try:
            self.data_service.remove_from_watchlist(self.active_watchlist, ticker)
        except StorageError as e:
            self.notify(str(e), severity="error")
            return
        self._reload_active_watchlist()

    def _reload_active_watchlist(self) -> None:
        """Reload data for the active watchlist tab."""
        name = self.active_watchlist
        if not name:
            return
        rows = self.data_service.get_watchlist_overview(name)
        panel = self.query_one("#watchlist-panel", WatchlistPanel)
        panel.refresh_watchlist(name, rows)

    # -- Focused asset tracking -----------------------------------------------

    def on_watchlist_table_cursor_changed(self, event) -> None:
        self.focused_asset = event.ticker

    def on_watchlist_table_row_activated(self, event) -> None:
        """Handle Enter on a focused DataTable row."""
        panel = self.query_one("#watchlist-panel", WatchlistPanel)
        if panel.in_detail:
            return
        detail = self.data_service.get_stock_detail(event.ticker)
        panel.show_detail(detail)
        self.focused_asset = event.ticker

    # -- Info screen -----------------------------------------------------------

    def action_show_info(self) -> None:
        from caracal.tui.screens.info import InfoScreen

        self.push_screen(InfoScreen(self.data_service))

    # -- Lifecycle ------------------------------------------------------------

    def on_unmount(self) -> None:
        if self._owns_data_service:
            self.data_service.close()

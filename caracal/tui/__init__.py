"""Caracal TUI — interactive terminal interface."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import reactive

from caracal.config import CONFIG_DIR, CaracalConfig
from caracal.tui.data import DataService
from caracal.tui.theme import CARACAL_THEME
from caracal.tui.widgets.footer import CaracalFooter
from caracal.tui.widgets.header import CaracalHeader
from caracal.tui.widgets.side_panel import SidePanel
from caracal.tui.widgets.watchlist_panel import WatchlistPanel
from caracal.tui.workers.daemon_connection import (
    DaemonConnected,
    DaemonDisconnected,
    DaemonEvent,
    daemon_connect,
    recv_ipc_message,
    send_ipc_message,
)

logger = logging.getLogger("caracal.tui")


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
        Binding("n", "focus_news", "News"),
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
    daemon_connected: reactive[bool] = reactive(False)

    def __init__(
        self,
        config: CaracalConfig,
        data_service: DataService | None = None,
        socket_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.data_service = data_service or DataService(config)
        self._owns_data_service = data_service is None
        self._watchlist_names: list[str] = []
        self._socket_path = socket_path or CONFIG_DIR / "caracal.sock"
        self._daemon_writer: asyncio.StreamWriter | None = None

    def compose(self) -> ComposeResult:
        yield CaracalHeader(show_clock=True, icon="◉")
        with Horizontal(id="main-layout"):
            yield WatchlistPanel(id="watchlist-panel")
            yield SidePanel(id="side-panel")
        yield CaracalFooter()

    async def on_mount(self) -> None:
        self.register_theme(CARACAL_THEME)
        self.theme = "caracal"
        self._watchlist_names = self.data_service.get_watchlist_names()
        await self._load_all_watchlists()
        # Start auto-refresh timer (30s)
        self.set_interval(30, self._auto_refresh)
        # Start daemon connection
        self._start_daemon_connection()

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
        self._load_news()

    def _update_footer_from_db(self) -> None:
        """Set footer timestamp from DB file modification time."""
        ts = self.data_service.get_last_fetch_time()
        if ts:
            self.query_one(CaracalFooter).last_updated = ts

    def _load_news(self) -> None:
        """Load news items into the side panel."""
        side = self.query_one("#side-panel", SidePanel)
        items = self.data_service.get_news()
        side.load_news(items)

    async def _auto_refresh(self) -> None:
        """Auto-refresh from DB cache."""
        self._load_news()
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

    # -- Daemon connection ----------------------------------------------------

    def _start_daemon_connection(self) -> None:
        """Start the daemon connection worker."""
        self.run_worker(self._daemon_worker(), exclusive=True, group="daemon")

    async def _daemon_worker(self) -> None:
        """Async worker: connect to daemon socket, subscribe, and listen."""
        reader = None
        writer = None
        try:
            reader, writer = await daemon_connect(self._socket_path)
            await send_ipc_message(writer, {"type": "subscribe"})
            response = await recv_ipc_message(reader)
            if response.get("status") != "ok":
                raise ConnectionError("Subscribe failed")
            self._daemon_writer = writer
            self.post_message(DaemonConnected())

            # Listen for events
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    data = json.loads(line.decode("utf-8").strip())
                    self.post_message(DaemonEvent(data))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
        except (
            ConnectionRefusedError,
            FileNotFoundError,
            ConnectionError,
            OSError,
            TimeoutError,
        ):
            pass
        finally:
            self._daemon_writer = None
            if writer is not None:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
            self.post_message(DaemonDisconnected())

    def on_daemon_connected(self, message: DaemonConnected) -> None:
        """Handle successful daemon connection."""
        self.daemon_connected = True
        footer = self.query_one(CaracalFooter)
        footer.daemon_status = "\u25cf Connected"

    def on_daemon_disconnected(self, message: DaemonDisconnected) -> None:
        """Handle daemon disconnection — switch to disconnected mode."""
        self.daemon_connected = False
        footer = self.query_one(CaracalFooter)
        footer.daemon_status = "\u25cb Disconnected"
        # Schedule reconnect after 10 seconds
        self.set_timer(10, self._start_daemon_connection)

    def on_daemon_event(self, message: DaemonEvent) -> None:
        """Handle an event received from the daemon."""
        data = message.data
        event_type = data.get("type")

        if event_type == "task_complete":
            task = data.get("task", "")
            if task in ("news", "NewsFetchTask"):
                self._load_news()
            if task in ("fetch", "FetchTask", "news", "NewsFetchTask"):
                self._refresh_visible_data()
        elif event_type == "data_update":
            self._refresh_visible_data()
        elif event_type == "shutdown":
            # Daemon shutting down — go disconnected
            self.daemon_connected = False
            self._daemon_writer = None
            footer = self.query_one(CaracalFooter)
            footer.daemon_status = "\u25cb Disconnected"

    def _refresh_visible_data(self) -> None:
        """Reload visible data from DB after a daemon update."""
        name = self.active_watchlist
        if name:
            panel = self.query_one("#watchlist-panel", WatchlistPanel)
            if not panel.in_detail:
                rows = self.data_service.get_watchlist_overview(name)
                panel.refresh_watchlist(name, rows)
        self._update_footer_from_db()

    async def _send_ipc_command(self, command: dict) -> None:
        """Send a command to the daemon via the active writer."""
        writer = self._daemon_writer
        if writer is None:
            return
        try:
            await send_ipc_message(writer, command)
        except (ConnectionResetError, BrokenPipeError, OSError):
            self._daemon_writer = None

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
        if self.daemon_connected and self._daemon_writer:
            await self._send_ipc_command({"type": "command", "cmd": "refresh"})
            return
        rows = self.data_service.refresh_watchlist_live(name)
        panel = self.query_one("#watchlist-panel", WatchlistPanel)
        panel.refresh_watchlist(name, rows)
        self.query_one(CaracalFooter).last_updated = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

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

        if self.daemon_connected and self._daemon_writer:
            await self._send_ipc_command(
                {"type": "command", "cmd": "create_watchlist", "name": name}
            )
        else:
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
        if self.daemon_connected and self._daemon_writer:
            await self._send_ipc_command(
                {
                    "type": "command",
                    "cmd": "delete_watchlist",
                    "name": self.active_watchlist,
                }
            )
        else:
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

    async def _on_add_result(self, tickers: list[str] | None) -> None:
        if tickers is None:
            return
        from caracal.storage.duckdb import StorageError

        if self.daemon_connected and self._daemon_writer:
            await self._send_ipc_command(
                {
                    "type": "command",
                    "cmd": "add_ticker",
                    "watchlist": self.active_watchlist,
                    "tickers": tickers,
                }
            )
        else:
            try:
                added, duplicates = self.data_service.add_to_watchlist(
                    self.active_watchlist, tickers
                )
            except StorageError as e:
                self.notify(str(e), severity="error")
                return
            if duplicates:
                self.notify(
                    f"Already in watchlist: {', '.join(duplicates)}",
                    severity="warning",
                )
            if not added:
                return
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

    async def _on_remove_result(self, confirmed: bool) -> None:
        if not confirmed:
            return
        ticker = self._pending_remove_ticker
        if not ticker:
            return
        from caracal.storage.duckdb import StorageError

        if self.daemon_connected and self._daemon_writer:
            await self._send_ipc_command(
                {
                    "type": "command",
                    "cmd": "remove_ticker",
                    "watchlist": self.active_watchlist,
                    "ticker": ticker,
                }
            )
        else:
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

    # -- News panel -----------------------------------------------------------

    def action_focus_news(self) -> None:
        """Move focus to the news side panel."""
        side = self.query_one("#side-panel", SidePanel)
        news_items = side.query("NewsItemWidget")
        if news_items:
            news_items.first().focus()
        else:
            side.focus()

    # -- Info screen -----------------------------------------------------------

    def action_show_info(self) -> None:
        from caracal.tui.screens.info import InfoScreen

        self.push_screen(InfoScreen(self.data_service))

    # -- Lifecycle ------------------------------------------------------------

    def on_unmount(self) -> None:
        if self._owns_data_service:
            self.data_service.close()

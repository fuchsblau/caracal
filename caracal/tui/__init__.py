"""Caracal TUI — interactive terminal interface."""

from __future__ import annotations

from textual.app import App
from textual.binding import Binding

from caracal.config import CaracalConfig
from caracal.tui.data import DataService


class CaracalApp(App):
    """Caracal interactive terminal interface."""

    CSS_PATH = "styles/app.tcss"
    TITLE = "Caracal"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("i", "show_info", "Info"),
    ]

    def __init__(
        self,
        config: CaracalConfig,
        data_service: DataService | None = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.data_service = data_service or DataService(config)
        self._owns_data_service = data_service is None

    def on_mount(self) -> None:
        from caracal.tui.screens.watchlist import WatchlistScreen

        self.push_screen(WatchlistScreen(self.data_service))

    def action_show_info(self) -> None:
        from caracal.tui.screens.info import InfoScreen

        self.push_screen(InfoScreen(self.data_service))

    def on_unmount(self) -> None:
        if self._owns_data_service:
            self.data_service.close()

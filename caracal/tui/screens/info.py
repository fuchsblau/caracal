"""Info screen — version, provider, config paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

if TYPE_CHECKING:
    from caracal.tui.data import DataService


class InfoScreen(ModalScreen):
    """Modal overlay showing app metadata."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("i", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    InfoScreen {
        align: center middle;
    }

    #info-dialog {
        width: 60;
        height: auto;
        max-height: 20;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #info-title {
        text-style: bold;
        color: #00bcd4;
        text-align: center;
        width: 100%;
    }

    .info-row {
        padding: 0 1;
    }
    """

    def __init__(self, data_service: DataService) -> None:
        super().__init__()
        self.data_service = data_service

    def compose(self) -> ComposeResult:
        info = self.data_service.get_app_info()
        with Vertical(id="info-dialog"):
            yield Static("Caracal", id="info-title")
            yield Static(f"[bold]Version:[/]  {info['version']}", classes="info-row")
            yield Static(f"[bold]Provider:[/] {info['provider']}", classes="info-row")
            yield Static(
                f"[bold]Config:[/]   {info['config_path']}",
                classes="info-row",
            )
            yield Static(f"[bold]Database:[/] {info['db_path']}", classes="info-row")

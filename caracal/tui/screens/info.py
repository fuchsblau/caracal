"""Info screen — placeholder for Task 5."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

if TYPE_CHECKING:
    from caracal.tui.data import DataService


class InfoScreen(Screen):
    """App information screen (stub — implemented in Task 5)."""

    def __init__(self, data_service: DataService) -> None:
        super().__init__()
        self.data_service = data_service

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Info screen (not yet implemented)")
        yield Footer()

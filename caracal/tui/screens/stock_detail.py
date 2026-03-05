"""Stock detail screen — placeholder for Task 4."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

if TYPE_CHECKING:
    from caracal.tui.data import DataService


class StockDetailScreen(Screen):
    """Detail view for a single stock (stub — implemented in Task 4)."""

    def __init__(self, ticker: str, data_service: DataService) -> None:
        super().__init__()
        self.ticker = ticker
        self.data_service = data_service

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Stock detail for {self.ticker} (not yet implemented)")
        yield Footer()

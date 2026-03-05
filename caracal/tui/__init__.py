"""Caracal TUI — interactive terminal interface."""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from caracal.config import CaracalConfig


class CaracalApp(App):
    """Caracal interactive terminal interface."""

    CSS_PATH = "styles/app.tcss"
    TITLE = "Caracal"

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self, config: CaracalConfig) -> None:
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

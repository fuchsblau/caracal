"""Remove ticker modal — confirmation dialog for removing a ticker."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class RemoveTickerModal(ModalScreen[bool]):
    """Confirmation dialog for removing a ticker from a watchlist.

    Dismisses with True (confirmed) or False (cancelled).
    """

    DEFAULT_CSS = """
    RemoveTickerModal {
        align: center middle;
    }

    #remove-dialog {
        width: 60;
        height: auto;
        max-height: 12;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #remove-title {
        text-style: bold;
        color: $error;
        text-align: center;
        width: 100%;
    }

    #remove-hint {
        color: $text-muted;
        padding: 0 1;
    }

    #remove-buttons {
        align: center middle;
        padding: 1 0 0 0;
    }

    #confirm-btn {
        margin: 0 1;
    }

    #cancel-btn {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, ticker: str) -> None:
        super().__init__()
        self.ticker = ticker

    def compose(self) -> ComposeResult:
        with Vertical(id="remove-dialog"):
            yield Label(f"Remove '{self.ticker}'?", id="remove-title")
            yield Label(
                "Ticker data in database is preserved.",
                id="remove-hint",
            )
            with Horizontal(id="remove-buttons"):
                yield Button("Remove", variant="error", id="confirm-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-btn")

    def action_cancel(self) -> None:
        self.dismiss(False)

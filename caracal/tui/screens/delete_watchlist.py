"""Delete watchlist modal — confirmation dialog."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class DeleteWatchlistModal(ModalScreen[bool]):
    """Confirmation dialog for deleting a watchlist.

    Dismisses with True (confirmed) or False (cancelled).
    """

    DEFAULT_CSS = """
    DeleteWatchlistModal {
        align: center middle;
    }

    #delete-dialog {
        width: 60;
        height: auto;
        max-height: 12;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #delete-title {
        text-style: bold;
        color: #f44336;
        text-align: center;
        width: 100%;
    }

    #delete-hint {
        color: $text-muted;
        padding: 0 1;
    }

    #delete-buttons {
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

    def __init__(self, watchlist_name: str) -> None:
        super().__init__()
        self.watchlist_name = watchlist_name

    def compose(self) -> ComposeResult:
        with Vertical(id="delete-dialog"):
            yield Label(f"Delete '{self.watchlist_name}'?", id="delete-title")
            yield Label(
                "Ticker data is preserved. Only the watchlist is removed.",
                id="delete-hint",
            )
            with Horizontal(id="delete-buttons"):
                yield Button("Delete", variant="error", id="confirm-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-btn")

    def action_cancel(self) -> None:
        self.dismiss(False)

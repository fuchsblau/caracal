"""Create watchlist modal — input dialog for new watchlist name."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label


class CreateWatchlistModal(ModalScreen[str | None]):
    """Modal dialog for creating a new watchlist.

    Dismisses with the watchlist name (str) or None on cancel.
    """

    DEFAULT_CSS = """
    CreateWatchlistModal {
        align: center middle;
    }

    #create-dialog {
        width: 60;
        height: auto;
        max-height: 12;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #create-title {
        text-style: bold;
        color: $primary;
        text-align: center;
        width: 100%;
    }

    #create-error {
        color: $error;
        height: 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="create-dialog"):
            yield Label("New Watchlist", id="create-title")
            yield Input(placeholder="Watchlist name...", id="create-input")
            yield Label("", id="create-error")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        if not name:
            self.query_one("#create-error", Label).update("Name must not be empty")
            return
        self.dismiss(name)

    def action_cancel(self) -> None:
        self.dismiss(None)

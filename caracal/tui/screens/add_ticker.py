"""Add ticker modal — input dialog for adding tickers to a watchlist."""

from __future__ import annotations

import re

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label


class AddTickerModal(ModalScreen[list[str] | None]):
    """Modal dialog for adding tickers to the active watchlist.

    Supports batch input: "AAPL" or "AAPL MSFT NVDA" or "AAPL, MSFT".
    Dismisses with list of uppercase ticker strings, or None on cancel.
    """

    DEFAULT_CSS = """
    AddTickerModal {
        align: center middle;
    }

    #add-dialog {
        width: 60;
        height: auto;
        max-height: 14;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #add-title {
        text-style: bold;
        color: #00bcd4;
        text-align: center;
        width: 100%;
    }

    #add-error {
        color: #f44336;
        height: 1;
    }

    #add-hint {
        color: $text-muted;
        height: 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="add-dialog"):
            yield Label("Add Ticker", id="add-title")
            yield Input(placeholder="AAPL or AAPL MSFT NVDA", id="add-input")
            yield Label("", id="add-error")
            yield Label(
                "Separate multiple tickers with spaces or commas",
                id="add-hint",
            )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        if not raw:
            self.query_one("#add-error", Label).update("Ticker must not be empty")
            return
        tickers = [t.upper() for t in re.split(r"[,\s]+", raw) if t]
        if not tickers:
            self.query_one("#add-error", Label).update("Ticker must not be empty")
            return
        self.dismiss(tickers)

    def action_cancel(self) -> None:
        self.dismiss(None)

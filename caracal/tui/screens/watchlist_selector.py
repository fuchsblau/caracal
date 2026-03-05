"""Watchlist selector modal — pick a watchlist from a list."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option


class WatchlistSelectorModal(ModalScreen[str | None]):
    """Modal dialog for selecting a watchlist.

    Dismisses with the watchlist name (str) or None on cancel.
    """

    DEFAULT_CSS = """
    WatchlistSelectorModal {
        align: center middle;
    }

    #selector-dialog {
        width: 60;
        height: auto;
        max-height: 22;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #selector-title {
        text-style: bold;
        color: #00bcd4;
        text-align: center;
        width: 100%;
    }

    #selector-options {
        height: auto;
        max-height: 16;
        margin: 1 0;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, watchlists: list[dict], current: str) -> None:
        super().__init__()
        self.watchlists = watchlists
        self.current = current

    def _build_options(self) -> list[Option]:
        """Build option items from watchlist data."""
        options = []
        for wl in self.watchlists:
            label = f"{wl['name']} ({wl['ticker_count']} ticker)"
            if wl["name"] == self.current:
                label = f"● {label}"
            options.append(Option(label, id=wl["name"]))
        return options

    def compose(self) -> ComposeResult:
        with Vertical(id="selector-dialog"):
            yield Label("Select Watchlist", id="selector-title")
            yield OptionList(*self._build_options(), id="selector-options")

    def on_mount(self) -> None:
        option_list = self.query_one("#selector-options", OptionList)
        option_list.highlighted = 0
        option_list.focus()

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        self.dismiss(str(event.option_id))

    def action_cancel(self) -> None:
        self.dismiss(None)

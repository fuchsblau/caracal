"""CaracalFooter — Footer with last-update timestamp."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Footer, Label


class CaracalFooter(Footer):
    """Footer that displays keybindings and a last-update timestamp."""

    last_updated: reactive[str] = reactive("—")

    def compose(self) -> ComposeResult:
        yield Label("Updated —", id="update-timestamp")
        yield from super().compose()

    def watch_last_updated(self, value: str) -> None:
        try:
            label = self.query_one("#update-timestamp", Label)
            label.update(f"Updated {value}")
        except Exception:
            pass

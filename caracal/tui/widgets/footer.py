"""CaracalFooter — Footer with last-update timestamp and daemon status."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Footer, Label


class CaracalFooter(Footer):
    """Footer that displays keybindings, a last-update timestamp, and daemon status."""

    last_updated: reactive[str] = reactive("—")
    daemon_status: reactive[str] = reactive("\u25cb Disconnected")

    def compose(self) -> ComposeResult:
        yield Label(self.daemon_status, id="daemon-status")
        yield Label(f"Updated {self.last_updated}", id="update-timestamp")
        yield from super().compose()

    def watch_last_updated(self, value: str) -> None:
        try:
            label = self.query_one("#update-timestamp", Label)
            label.update(f"Updated {value}")
        except Exception:
            pass

    def watch_daemon_status(self, value: str) -> None:
        try:
            label = self.query_one("#daemon-status", Label)
            label.update(value)
        except Exception:
            pass

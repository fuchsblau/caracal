"""SidePanel -- collapsed placeholder for future widgets."""

from __future__ import annotations

from textual.widget import Widget
from textual.widgets import Static


class SidePanel(Widget):
    """Collapsed side panel for future support widgets."""

    DEFAULT_CSS = """
    SidePanel {
        display: none;
        width: 30%;
        height: 100%;
        border-left: solid $accent;
    }
    """

    def compose(self):
        yield Static("Support widgets will appear here", id="side-placeholder")

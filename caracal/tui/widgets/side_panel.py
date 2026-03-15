"""SidePanel -- news panel for the TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from caracal.tui.widgets.news_item import NewsItemWidget


class SidePanel(Widget, can_focus=True):
    """Side panel displaying recent news items."""

    DEFAULT_CSS = """
    SidePanel {
        width: 35%;
        height: 100%;
        border-left: solid $accent;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("News", id="news-title")
        yield VerticalScroll(id="news-scroll")

    def load_news(self, items: list[dict]) -> None:
        """Populate the news panel with items (max 50)."""
        scroll = self.query_one("#news-scroll", VerticalScroll)
        scroll.remove_children()
        for item in items[:50]:
            widget = NewsItemWidget(
                headline=item.get("headline", ""),
                feed=item.get("feed", ""),
                url=item.get("url"),
                time_ago=item.get("time_ago", ""),
            )
            scroll.mount(widget)

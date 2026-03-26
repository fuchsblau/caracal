"""NewsItemWidget -- compact display of a single news item."""

from __future__ import annotations

import webbrowser
from urllib.parse import urlparse

from rich.text import Text
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Static

from caracal.tui.theme import COLOR_MUTED, COLOR_PRICE

_SAFE_SCHEMES = {"http", "https"}


def is_safe_url(url: str | None) -> bool:
    """Return True only if *url* has an http or https scheme."""
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme in _SAFE_SCHEMES


class NewsItemWidget(Widget, can_focus=True):
    """A single news item row: [feed] headline                   2h."""

    BINDINGS = [
        Binding("enter", "open_url", "Open", show=False),
    ]

    DEFAULT_CSS = """
    NewsItemWidget {
        height: auto;
        padding: 0 1;
    }
    NewsItemWidget:focus {
        background: $primary 20%;
    }
    NewsItemWidget:hover {
        background: $primary 10%;
    }
    """

    def __init__(
        self,
        headline: str,
        feed: str,
        url: str | None,
        time_ago: str,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.headline = headline
        self.feed = feed
        self.url = url
        self.time_ago = time_ago

    def compose(self):
        text = Text()
        text.append(f"[{self.feed}]", style=f"bold {COLOR_PRICE}")
        text.append(" ")
        text.append(self.headline)
        text.append(f"  {self.time_ago}", style=COLOR_MUTED)
        yield Static(text, id="news-line")

    def action_open_url(self) -> None:
        """Open the news URL in the default browser."""
        if is_safe_url(self.url):
            webbrowser.open(self.url)

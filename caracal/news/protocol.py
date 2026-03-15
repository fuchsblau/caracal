"""News source protocol and data types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class NewsItem:
    """A single news item from any news source."""

    id: str  # RSS <guid>
    source: str  # e.g. "reuters"
    feed: str  # e.g. "business", "markets", "tech"
    headline: str
    summary: str | None
    url: str | None
    published_at: datetime


class NewsSource(Protocol):
    """Interface for news data providers."""

    def fetch(self) -> list[NewsItem]: ...

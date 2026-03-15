"""News service for TUI -- provides formatted news items."""

from __future__ import annotations

import logging
from datetime import datetime

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage

logger = logging.getLogger("caracal")


def _relative_timestamp(published_at: datetime | str | None) -> str:
    """Format a datetime as a short relative timestamp (e.g. '2h', '5m', '1d')."""
    if published_at is None:
        return ""
    if isinstance(published_at, str):
        try:
            published_at = datetime.fromisoformat(published_at)
        except (ValueError, TypeError):
            return ""
    now = datetime.now(tz=published_at.tzinfo if published_at.tzinfo else None)
    delta = now - published_at
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0
    minutes = total_seconds // 60
    hours = total_seconds // 3600
    days = total_seconds // 86400
    if days >= 1:
        return f"{days}d"
    if hours >= 1:
        return f"{hours}h"
    if minutes >= 1:
        return f"{minutes}m"
    return "now"


class NewsService:
    """News retrieval -- extracted from DataService."""

    def __init__(self, config: CaracalConfig, storage: DuckDBStorage) -> None:
        self._storage = storage

    def get_recent_news(self, limit: int = 50) -> list[dict]:
        """Return recent news items with relative timestamps.

        Each dict has keys: id, source, feed, headline, summary, url,
        published_at, fetched_at, time_ago.
        """
        try:
            items = self._storage.get_news(limit=limit)
        except Exception:
            logger.warning("Failed to load news from storage")
            return []
        for item in items:
            item["time_ago"] = _relative_timestamp(item.get("published_at"))
        return items

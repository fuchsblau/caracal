"""Reuters RSS news source."""

from __future__ import annotations

import logging
from calendar import timegm
from datetime import UTC, datetime

import feedparser

from caracal.news.protocol import NewsItem

logger = logging.getLogger("caracal.news")


class ReutersRSSSource:
    """Fetch news from Reuters RSS feeds."""

    FEEDS: dict[str, str] = {
        "business": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",
        "markets": "https://www.reutersagency.com/feed/?best-topics=markets&post_type=best",
        "tech": "https://www.reutersagency.com/feed/?best-topics=tech&post_type=best",
    }

    def fetch(self) -> list[NewsItem]:
        """Fetch news items from all Reuters RSS feeds.

        Errors on individual feeds are logged and skipped so that
        remaining feeds are still processed.
        """
        items: list[NewsItem] = []
        for feed_name, url in self.FEEDS.items():
            try:
                items.extend(self._parse_feed(feed_name, url))
            except Exception:
                logger.error("Failed to fetch feed %s", feed_name, exc_info=True)
        return items

    def _parse_feed(self, feed_name: str, url: str) -> list[NewsItem]:
        """Parse a single RSS feed into NewsItem objects."""
        parsed = feedparser.parse(url)

        if parsed.bozo and not parsed.entries:
            raise ValueError(
                f"Feed parse error for {feed_name}: {parsed.bozo_exception}"
            )

        items: list[NewsItem] = []
        for entry in parsed.entries:
            item = self._entry_to_item(entry, feed_name)
            if item is not None:
                items.append(item)
        return items

    def _entry_to_item(self, entry: dict, feed_name: str) -> NewsItem | None:
        """Convert a feedparser entry to a NewsItem."""
        guid = getattr(entry, "id", None) or getattr(entry, "link", None)
        if not guid:
            return None

        headline = getattr(entry, "title", None)
        if not headline:
            return None

        summary = getattr(entry, "summary", None)
        url = getattr(entry, "link", None)
        published_at = self._extract_datetime(entry)

        return NewsItem(
            id=guid,
            source="reuters",
            feed=feed_name,
            headline=headline,
            summary=summary,
            url=url,
            published_at=published_at,
        )

    @staticmethod
    def _extract_datetime(entry: dict) -> datetime:
        """Extract published datetime from a feed entry."""
        time_struct = getattr(entry, "published_parsed", None) or getattr(
            entry, "updated_parsed", None
        )
        if time_struct:
            return datetime.fromtimestamp(timegm(time_struct), tz=UTC)
        return datetime.now(tz=UTC)

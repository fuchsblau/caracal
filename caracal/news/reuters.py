"""RSS news sources for financial news."""

from __future__ import annotations

import logging
from calendar import timegm
from datetime import UTC, datetime

from urllib.request import Request, urlopen

import feedparser

from caracal.news.protocol import NewsItem

logger = logging.getLogger("caracal.news")

FEED_TIMEOUT = 30


class ReutersRSSSource:
    """Fetch news from financial RSS feeds."""

    FEEDS: dict[str, tuple[str, str]] = {
        "markets": (
            "bloomberg",
            "https://feeds.bloomberg.com/markets/news.rss",
        ),
        "general": (
            "marketwatch",
            "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
        ),
        "top-news": (
            "cnbc",
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        ),
    }

    def fetch(self) -> list[NewsItem]:
        """Fetch news items from all RSS feeds.

        Errors on individual feeds are logged and skipped so that
        remaining feeds are still processed.
        """
        items: list[NewsItem] = []
        for feed_name, (source, url) in self.FEEDS.items():
            try:
                items.extend(self._parse_feed(feed_name, source, url))
            except Exception:
                logger.error("Failed to fetch feed %s", feed_name, exc_info=True)
        return items

    def _parse_feed(
        self, feed_name: str, source: str, url: str
    ) -> list[NewsItem]:
        """Parse a single RSS feed into NewsItem objects."""
        response = urlopen(Request(url), timeout=FEED_TIMEOUT)
        raw = response.read()
        parsed = feedparser.parse(raw)

        if parsed.bozo and not parsed.entries:
            raise ValueError(
                f"Feed parse error for {feed_name}: {parsed.bozo_exception}"
            )

        items: list[NewsItem] = []
        for entry in parsed.entries:
            item = self._entry_to_item(entry, source, feed_name)
            if item is not None:
                items.append(item)
        return items

    def _entry_to_item(
        self, entry: dict, source: str, feed_name: str
    ) -> NewsItem | None:
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
            source=source,
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

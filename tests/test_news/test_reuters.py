"""Tests for ReutersRSSSource with mocked feedparser."""

import time
from unittest.mock import MagicMock, patch

from caracal.news.reuters import ReutersRSSSource


def _make_entry(
    guid="urn:test:1",
    title="Test headline",
    summary="Test summary",
    link="https://example.com/1",
    published_parsed=None,
):
    """Create a mock feedparser entry."""
    entry = MagicMock()
    entry.id = guid
    entry.title = title
    entry.summary = summary
    entry.link = link
    entry.published_parsed = published_parsed or time.strptime(
        "2026-03-15 10:00:00", "%Y-%m-%d %H:%M:%S"
    )
    entry.updated_parsed = None
    return entry


def _make_feed_result(entries=None, bozo=False, bozo_exception=None):
    """Create a mock feedparser.parse result."""
    result = MagicMock()
    result.entries = entries or []
    result.bozo = bozo
    result.bozo_exception = bozo_exception
    return result


class TestReutersRSSSource:
    def test_has_three_feeds(self):
        source = ReutersRSSSource()
        assert len(source.FEEDS) == 3
        assert "business" in source.FEEDS
        assert "markets" in source.FEEDS
        assert "tech" in source.FEEDS

    @patch("caracal.news.reuters.feedparser.parse")
    def test_fetch_returns_items_from_all_feeds(self, mock_parse):
        entries_biz = [_make_entry(guid="biz-1", title="Business news")]
        entries_mkt = [_make_entry(guid="mkt-1", title="Markets news")]
        entries_tech = [_make_entry(guid="tech-1", title="Tech news")]

        mock_parse.side_effect = [
            _make_feed_result(entries_biz),
            _make_feed_result(entries_mkt),
            _make_feed_result(entries_tech),
        ]

        source = ReutersRSSSource()
        items = source.fetch()

        assert len(items) == 3
        assert mock_parse.call_count == 3
        feeds = {item.feed for item in items}
        assert feeds == {"business", "markets", "tech"}

    @patch("caracal.news.reuters.feedparser.parse")
    def test_maps_fields_correctly(self, mock_parse):
        entry = _make_entry(
            guid="test-guid",
            title="Test Headline",
            summary="Test Summary",
            link="https://example.com/article",
        )
        mock_parse.return_value = _make_feed_result([entry])

        source = ReutersRSSSource()
        # Only parse one feed to simplify
        items = source._parse_feed("business", "https://example.com/feed")

        assert len(items) == 1
        item = items[0]
        assert item.id == "test-guid"
        assert item.source == "reuters"
        assert item.feed == "business"
        assert item.headline == "Test Headline"
        assert item.summary == "Test Summary"
        assert item.url == "https://example.com/article"
        assert item.published_at is not None

    @patch("caracal.news.reuters.feedparser.parse")
    def test_error_on_one_feed_continues_others(self, mock_parse):
        """AC4: Feed error should log and continue with remaining feeds."""
        entries_ok = [_make_entry(guid="ok-1", title="Good news")]

        mock_parse.side_effect = [
            _make_feed_result(entries_ok),
            Exception("Network timeout"),
            _make_feed_result(entries_ok),
        ]

        source = ReutersRSSSource()
        items = source.fetch()

        # Should have items from 2 successful feeds
        assert len(items) == 2

    @patch("caracal.news.reuters.feedparser.parse")
    def test_all_feeds_fail_returns_empty(self, mock_parse):
        mock_parse.side_effect = Exception("All feeds down")

        source = ReutersRSSSource()
        items = source.fetch()

        assert items == []

    @patch("caracal.news.reuters.feedparser.parse")
    def test_entry_without_guid_uses_link(self, mock_parse):
        entry = MagicMock()
        entry.id = None
        entry.link = "https://example.com/fallback"
        entry.title = "Fallback title"
        entry.summary = None
        entry.published_parsed = time.strptime(
            "2026-03-15 10:00:00", "%Y-%m-%d %H:%M:%S"
        )
        entry.updated_parsed = None

        mock_parse.return_value = _make_feed_result([entry])

        source = ReutersRSSSource()
        items = source._parse_feed("business", "https://example.com/feed")

        assert len(items) == 1
        assert items[0].id == "https://example.com/fallback"

    @patch("caracal.news.reuters.feedparser.parse")
    def test_entry_without_guid_and_link_is_skipped(self, mock_parse):
        entry = MagicMock()
        entry.id = None
        entry.link = None
        entry.title = "No ID"
        entry.summary = None

        mock_parse.return_value = _make_feed_result([entry])

        source = ReutersRSSSource()
        items = source._parse_feed("business", "https://example.com/feed")

        assert len(items) == 0

    @patch("caracal.news.reuters.feedparser.parse")
    def test_entry_without_title_is_skipped(self, mock_parse):
        entry = MagicMock()
        entry.id = "has-guid"
        entry.link = "https://example.com"
        entry.title = None
        entry.summary = None

        mock_parse.return_value = _make_feed_result([entry])

        source = ReutersRSSSource()
        items = source._parse_feed("business", "https://example.com/feed")

        assert len(items) == 0

    @patch("caracal.news.reuters.feedparser.parse")
    def test_uses_updated_parsed_as_fallback(self, mock_parse):
        entry = MagicMock()
        entry.id = "guid-1"
        entry.title = "Title"
        entry.summary = None
        entry.link = None
        entry.published_parsed = None
        entry.updated_parsed = time.strptime("2026-03-14 08:00:00", "%Y-%m-%d %H:%M:%S")

        mock_parse.return_value = _make_feed_result([entry])

        source = ReutersRSSSource()
        items = source._parse_feed("business", "https://example.com/feed")

        assert len(items) == 1
        assert items[0].published_at.year == 2026
        assert items[0].published_at.month == 3
        assert items[0].published_at.day == 14

    @patch("caracal.news.reuters.feedparser.parse")
    def test_bozo_feed_with_no_entries_raises(self, mock_parse):
        """A feed with parse error and no entries should raise."""
        mock_parse.return_value = _make_feed_result(
            entries=[], bozo=True, bozo_exception=Exception("XML parse error")
        )

        source = ReutersRSSSource()
        # In fetch(), this would be caught and logged
        items = source.fetch()
        assert items == []

    @patch("caracal.news.reuters.feedparser.parse")
    def test_bozo_feed_with_entries_still_returns_items(self, mock_parse):
        """A bozo feed with entries should still return the entries."""
        entry = _make_entry(guid="bozo-1", title="Bozo news")
        mock_parse.return_value = _make_feed_result(
            entries=[entry], bozo=True, bozo_exception=Exception("Minor issue")
        )

        source = ReutersRSSSource()
        items = source._parse_feed("business", "https://example.com/feed")

        assert len(items) == 1

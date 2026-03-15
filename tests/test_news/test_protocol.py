"""Tests for news protocol and data types."""

from datetime import UTC, datetime

from caracal.news.protocol import NewsItem


class TestNewsItem:
    def test_creation_with_all_fields(self):
        item = NewsItem(
            id="guid-1",
            source="reuters",
            feed="business",
            headline="Test headline",
            summary="Test summary",
            url="https://example.com/1",
            published_at=datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC),
        )
        assert item.id == "guid-1"
        assert item.source == "reuters"
        assert item.feed == "business"
        assert item.headline == "Test headline"
        assert item.summary == "Test summary"
        assert item.url == "https://example.com/1"
        assert item.published_at == datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC)

    def test_creation_with_optional_none(self):
        item = NewsItem(
            id="guid-2",
            source="reuters",
            feed="tech",
            headline="Headline only",
            summary=None,
            url=None,
            published_at=datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC),
        )
        assert item.summary is None
        assert item.url is None

    def test_equality(self):
        kwargs = {
            "id": "guid-1",
            "source": "reuters",
            "feed": "business",
            "headline": "Test",
            "summary": None,
            "url": None,
            "published_at": datetime(2026, 3, 15, tzinfo=UTC),
        }
        assert NewsItem(**kwargs) == NewsItem(**kwargs)

    def test_different_items_not_equal(self):
        base = {
            "source": "reuters",
            "feed": "business",
            "headline": "Test",
            "summary": None,
            "url": None,
            "published_at": datetime(2026, 3, 15, tzinfo=UTC),
        }
        item1 = NewsItem(id="guid-1", **base)
        item2 = NewsItem(id="guid-2", **base)
        assert item1 != item2

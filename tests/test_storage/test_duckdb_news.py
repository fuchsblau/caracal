"""Tests for DuckDB news storage methods."""

from datetime import UTC, datetime, timedelta

import pytest

from caracal.news.protocol import NewsItem
from caracal.storage.duckdb import DuckDBStorage


@pytest.fixture
def storage():
    """In-memory DuckDB storage for news storage tests."""
    s = DuckDBStorage(":memory:")
    yield s
    s.close()


def _make_item(
    id: str = "guid-1",
    source: str = "reuters",
    feed: str = "business",
    headline: str = "Test headline",
    summary: str | None = "Test summary",
    url: str | None = "https://example.com/1",
    published_at: datetime | None = None,
) -> NewsItem:
    return NewsItem(
        id=id,
        source=source,
        feed=feed,
        headline=headline,
        summary=summary,
        url=url,
        published_at=published_at or datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC),
    )


class TestStoreNews:
    def test_store_single_item(self, storage):
        items = [_make_item()]
        count = storage.store_news(items)
        assert count == 1

    def test_store_multiple_items(self, storage):
        items = [
            _make_item(id="guid-1"),
            _make_item(id="guid-2", headline="Second"),
            _make_item(id="guid-3", headline="Third"),
        ]
        count = storage.store_news(items)
        assert count == 3

    def test_store_empty_list(self, storage):
        count = storage.store_news([])
        assert count == 0

    def test_deduplication_same_guid(self, storage):
        """AC3: Known GUID should not create duplicates."""
        items = [_make_item(id="dup-1")]
        storage.store_news(items)
        count = storage.store_news(items)
        assert count == 0
        assert storage.get_news_count() == 1

    def test_deduplication_mixed(self, storage):
        """Storing mix of new and existing items returns only new count."""
        storage.store_news([_make_item(id="existing")])
        items = [
            _make_item(id="existing"),
            _make_item(id="new-1"),
            _make_item(id="new-2"),
        ]
        count = storage.store_news(items)
        assert count == 2
        assert storage.get_news_count() == 3

    def test_stores_none_summary_and_url(self, storage):
        items = [_make_item(summary=None, url=None)]
        storage.store_news(items)
        news = storage.get_news(limit=1)
        assert len(news) == 1
        assert news[0]["summary"] is None
        assert news[0]["url"] is None


class TestGetNews:
    def test_returns_empty_when_no_news(self, storage):
        news = storage.get_news()
        assert news == []

    def test_returns_items_ordered_by_published_at_desc(self, storage):
        items = [
            _make_item(
                id="old",
                published_at=datetime(2026, 3, 14, 10, 0, 0, tzinfo=UTC),
            ),
            _make_item(
                id="new",
                published_at=datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC),
            ),
        ]
        storage.store_news(items)
        news = storage.get_news()
        assert news[0]["id"] == "new"
        assert news[1]["id"] == "old"

    def test_respects_limit(self, storage):
        items = [_make_item(id=f"guid-{i}") for i in range(10)]
        storage.store_news(items)
        news = storage.get_news(limit=3)
        assert len(news) == 3

    def test_returns_all_fields(self, storage):
        items = [_make_item()]
        storage.store_news(items)
        news = storage.get_news(limit=1)
        assert len(news) == 1
        item = news[0]
        assert "id" in item
        assert "source" in item
        assert "feed" in item
        assert "headline" in item
        assert "summary" in item
        assert "url" in item
        assert "published_at" in item
        assert "fetched_at" in item


class TestGetNewsCount:
    def test_count_empty(self, storage):
        assert storage.get_news_count() == 0

    def test_count_after_inserts(self, storage):
        items = [_make_item(id=f"guid-{i}") for i in range(5)]
        storage.store_news(items)
        assert storage.get_news_count() == 5


def _insert_with_fetched_at(
    storage: DuckDBStorage, id: str, fetched_at: datetime
) -> None:
    """Insert a news item with a specific fetched_at timestamp."""
    storage._conn.execute(
        "INSERT INTO news (id, source, feed, headline, summary, url,"
        " published_at, fetched_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            id,
            "reuters",
            "business",
            f"Headline {id}",
            f"Summary {id}",
            f"https://example.com/{id}",
            fetched_at,
            fetched_at,
        ],
    )


class TestDeleteOldNews:
    def test_deletes_old_items(self, storage):
        now = datetime.now(tz=UTC)
        _insert_with_fetched_at(storage, "old-1", now - timedelta(days=10))
        _insert_with_fetched_at(storage, "old-2", now - timedelta(days=8))
        _insert_with_fetched_at(storage, "recent", now - timedelta(days=1))

        deleted = storage.delete_old_news(retention_days=7)

        assert deleted == 2
        assert storage.get_news_count() == 1

    def test_respects_retention_days(self, storage):
        now = datetime.now(tz=UTC)
        _insert_with_fetched_at(storage, "keep", now - timedelta(days=10))
        _insert_with_fetched_at(storage, "delete", now - timedelta(days=20))

        deleted = storage.delete_old_news(retention_days=14)

        assert deleted == 1
        assert storage.get_news_count() == 1

    def test_default_retention_7_days(self, storage):
        now = datetime.now(tz=UTC)
        _insert_with_fetched_at(storage, "old", now - timedelta(days=8))
        _insert_with_fetched_at(storage, "recent", now - timedelta(days=6))

        deleted = storage.delete_old_news()

        assert deleted == 1
        assert storage.get_news_count() == 1

    def test_nothing_to_delete(self, storage):
        now = datetime.now(tz=UTC)
        _insert_with_fetched_at(storage, "recent", now - timedelta(hours=1))

        deleted = storage.delete_old_news()

        assert deleted == 0
        assert storage.get_news_count() == 1

    def test_empty_table(self, storage):
        deleted = storage.delete_old_news()
        assert deleted == 0


class TestDeleteOldNewsParameterized:
    def test_delete_old_news_uses_parameterized_query(self, storage):
        """Verify delete_old_news works correctly with parameterized approach."""
        from datetime import datetime, timedelta

        from caracal.news.protocol import NewsItem

        old_item = NewsItem(
            id="old-1",
            source="test",
            feed="test",
            headline="Old news",
            summary=None,
            url=None,
            published_at=datetime.now() - timedelta(days=30),
        )
        new_item = NewsItem(
            id="new-1",
            source="test",
            feed="test",
            headline="New news",
            summary=None,
            url=None,
            published_at=datetime.now(),
        )
        storage.store_news([old_item, new_item])

        # Manually backdate the fetched_at of old item
        storage._conn.execute(
            "UPDATE news SET fetched_at = CURRENT_TIMESTAMP - INTERVAL '30 days' WHERE id = 'old-1'"
        )

        deleted = storage.delete_old_news(retention_days=7)
        assert deleted == 1
        assert storage.get_news_count() == 1

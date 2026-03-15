"""Tests for the NewsFetchTask daemon task."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from caracal.config import CaracalConfig
from caracal.daemon.registry import TaskContext
from caracal.daemon.tasks.news import NewsFetchTask
from caracal.news.protocol import NewsItem
from caracal.storage.duckdb import DuckDBStorage


def _make_items(count: int = 3) -> list[NewsItem]:
    """Create sample news items."""
    return [
        NewsItem(
            id=f"guid-{i}",
            source="reuters",
            feed="business",
            headline=f"Headline {i}",
            summary=f"Summary {i}",
            url=f"https://example.com/{i}",
            published_at=datetime(2026, 3, 15, 10 + i, 0, 0, tzinfo=UTC),
        )
        for i in range(count)
    ]


@pytest.fixture
def context():
    storage = DuckDBStorage(":memory:")
    ctx = TaskContext(db=storage, config=CaracalConfig())
    yield ctx
    storage.close()


class TestNewsFetchTask:
    def test_task_name(self):
        assert NewsFetchTask().name == "news"

    @pytest.mark.asyncio
    async def test_fetch_stores_items(self, context):
        items = _make_items(3)

        with patch("caracal.daemon.tasks.news.ReutersRSSSource") as mock_source_cls:
            mock_source_cls.return_value.fetch.return_value = items
            task = NewsFetchTask()
            result = await task.run(context)

        assert result.status == "ok"
        assert result.items_processed == 3
        assert context.db.get_news_count() == 3

    @pytest.mark.asyncio
    async def test_no_items_returns_ok(self, context):
        with patch("caracal.daemon.tasks.news.ReutersRSSSource") as mock_source_cls:
            mock_source_cls.return_value.fetch.return_value = []
            task = NewsFetchTask()
            result = await task.run(context)

        assert result.status == "ok"
        assert result.items_processed == 0

    @pytest.mark.asyncio
    async def test_fetch_error_returns_error_result(self, context):
        with patch("caracal.daemon.tasks.news.ReutersRSSSource") as mock_source_cls:
            mock_source_cls.return_value.fetch.side_effect = Exception("Network error")
            task = NewsFetchTask()
            result = await task.run(context)

        assert result.status == "error"
        assert "Network error" in result.message

    @pytest.mark.asyncio
    async def test_deduplication_on_second_run(self, context):
        """Running twice with the same items should not create duplicates."""
        items = _make_items(2)

        with patch("caracal.daemon.tasks.news.ReutersRSSSource") as mock_source_cls:
            mock_source_cls.return_value.fetch.return_value = items
            task = NewsFetchTask()

            result1 = await task.run(context)
            assert result1.items_processed == 2

            result2 = await task.run(context)
            assert result2.items_processed == 0

        assert context.db.get_news_count() == 2

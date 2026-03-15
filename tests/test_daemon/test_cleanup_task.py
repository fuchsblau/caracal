"""Tests for the CleanupTask daemon task."""

from datetime import UTC, datetime, timedelta

import pytest

from caracal.config import CaracalConfig, WorkerConfig
from caracal.daemon.registry import TaskContext
from caracal.daemon.tasks.cleanup import CleanupTask
from caracal.news.protocol import NewsItem
from caracal.storage.duckdb import DuckDBStorage


def _make_item(id: str, published_at: datetime) -> NewsItem:
    return NewsItem(
        id=id,
        source="reuters",
        feed="business",
        headline=f"Headline {id}",
        summary=f"Summary {id}",
        url=f"https://example.com/{id}",
        published_at=published_at,
    )


def _insert_news_with_fetched_at(
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


@pytest.fixture
def storage():
    s = DuckDBStorage(":memory:")
    yield s
    s.close()


@pytest.fixture
def context(storage):
    return TaskContext(db=storage, config=CaracalConfig())


class TestCleanupTask:
    def test_task_name(self):
        assert CleanupTask().name == "cleanup"

    @pytest.mark.asyncio
    async def test_deletes_old_news(self, storage, context):
        """News older than 7 days (default) should be deleted."""
        now = datetime.now(tz=UTC)
        old = now - timedelta(days=10)
        recent = now - timedelta(days=1)

        _insert_news_with_fetched_at(storage, "old-1", old)
        _insert_news_with_fetched_at(storage, "old-2", old)
        _insert_news_with_fetched_at(storage, "recent-1", recent)
        assert storage.get_news_count() == 3

        task = CleanupTask()
        result = await task.run(context)

        assert result.status == "ok"
        assert result.items_processed == 2
        assert storage.get_news_count() == 1

    @pytest.mark.asyncio
    async def test_uses_configured_retention_days(self, storage):
        """Custom retention_days from config should be respected."""
        worker = WorkerConfig(retention_days=14)
        config = CaracalConfig(worker=worker)
        ctx = TaskContext(db=storage, config=config)

        now = datetime.now(tz=UTC)
        # 10 days old — within 14-day retention, should be kept
        _insert_news_with_fetched_at(storage, "keep", now - timedelta(days=10))
        # 20 days old — beyond 14-day retention, should be deleted
        _insert_news_with_fetched_at(storage, "delete", now - timedelta(days=20))

        task = CleanupTask()
        result = await task.run(ctx)

        assert result.status == "ok"
        assert result.items_processed == 1
        assert storage.get_news_count() == 1

    @pytest.mark.asyncio
    async def test_nothing_to_delete(self, storage, context):
        """When no old news exists, cleanup should delete nothing."""
        now = datetime.now(tz=UTC)
        _insert_news_with_fetched_at(storage, "recent-1", now - timedelta(days=1))
        _insert_news_with_fetched_at(storage, "recent-2", now - timedelta(hours=2))

        task = CleanupTask()
        result = await task.run(context)

        assert result.status == "ok"
        assert result.items_processed == 0
        assert storage.get_news_count() == 2

    @pytest.mark.asyncio
    async def test_empty_database(self, context):
        """Cleanup on empty database should succeed with 0 items."""
        task = CleanupTask()
        result = await task.run(context)

        assert result.status == "ok"
        assert result.items_processed == 0

    @pytest.mark.asyncio
    async def test_returns_correct_task_result(self, storage, context):
        """TaskResult should have status='ok' and correct items_processed."""
        now = datetime.now(tz=UTC)
        for i in range(5):
            _insert_news_with_fetched_at(storage, f"old-{i}", now - timedelta(days=10))

        task = CleanupTask()
        result = await task.run(context)

        assert result.status == "ok"
        assert result.items_processed == 5
        assert result.message is None

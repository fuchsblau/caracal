"""Tests for NewsService."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from caracal.config import CaracalConfig
from caracal.news.protocol import NewsItem
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui.services.news_service import (
    NewsService,
    _relative_timestamp,
)

# ---------------------------------------------------------------------------
# _relative_timestamp
# ---------------------------------------------------------------------------


class TestRelativeTimestamp:
    def test_none_returns_empty(self):
        assert _relative_timestamp(None) == ""

    def test_just_now(self):
        now = datetime.now()
        assert _relative_timestamp(now) == "now"

    def test_minutes_ago(self):
        t = datetime.now() - timedelta(minutes=5)
        assert _relative_timestamp(t) == "5m"

    def test_hours_ago(self):
        t = datetime.now() - timedelta(hours=2)
        assert _relative_timestamp(t) == "2h"

    def test_days_ago(self):
        t = datetime.now() - timedelta(days=3)
        assert _relative_timestamp(t) == "3d"

    def test_1_hour_boundary(self):
        t = datetime.now() - timedelta(minutes=60)
        assert _relative_timestamp(t) == "1h"

    def test_1_day_boundary(self):
        t = datetime.now() - timedelta(hours=24)
        assert _relative_timestamp(t) == "1d"

    def test_string_datetime(self):
        t = datetime.now() - timedelta(hours=1)
        result = _relative_timestamp(t.isoformat())
        assert result == "1h"

    def test_invalid_string_returns_empty(self):
        assert _relative_timestamp("not-a-date") == ""

    def test_future_timestamp_returns_now(self):
        t = datetime.now() + timedelta(hours=1)
        assert _relative_timestamp(t) == "now"


# ---------------------------------------------------------------------------
# NewsService
# ---------------------------------------------------------------------------


def _make_news_item(
    id: str = "1",
    headline: str = "Test headline",
    feed: str = "markets",
    published_at: datetime | None = None,
    url: str | None = "https://example.com",
) -> NewsItem:
    return NewsItem(
        id=id,
        source="reuters",
        feed=feed,
        headline=headline,
        summary="Test summary",
        url=url,
        published_at=published_at or datetime.now(),
    )


@pytest.fixture
def storage():
    s = DuckDBStorage(":memory:")
    yield s
    s.close()


@pytest.fixture
def config():
    return CaracalConfig(db_path=":memory:")


@pytest.fixture
def news_service(config, storage):
    return NewsService(config, storage)


class TestNewsService:
    def test_get_recent_news_empty(self, news_service):
        items = news_service.get_recent_news()
        assert items == []

    def test_get_recent_news_with_data(self, news_service, storage):
        storage.store_news([_make_news_item()])
        items = news_service.get_recent_news()
        assert len(items) == 1
        assert items[0]["headline"] == "Test headline"
        assert "time_ago" in items[0]

    def test_get_recent_news_respects_limit(self, news_service, storage):
        news_items = [
            _make_news_item(
                id=str(i),
                headline=f"Headline {i}",
                published_at=datetime.now() - timedelta(minutes=i),
            )
            for i in range(10)
        ]
        storage.store_news(news_items)
        items = news_service.get_recent_news(limit=5)
        assert len(items) == 5

    def test_get_recent_news_adds_time_ago(self, news_service, storage):
        storage.store_news(
            [
                _make_news_item(
                    published_at=datetime.now() - timedelta(hours=3),
                )
            ]
        )
        items = news_service.get_recent_news()
        assert items[0]["time_ago"] == "3h"

    def test_get_recent_news_sorted_newest_first(self, news_service, storage):
        storage.store_news(
            [
                _make_news_item(
                    id="old",
                    headline="Old news",
                    published_at=datetime.now() - timedelta(hours=5),
                ),
                _make_news_item(
                    id="new",
                    headline="New news",
                    published_at=datetime.now() - timedelta(minutes=5),
                ),
            ]
        )
        items = news_service.get_recent_news()
        assert items[0]["headline"] == "New news"
        assert items[1]["headline"] == "Old news"

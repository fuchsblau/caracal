"""Fixtures for news tests."""

from datetime import UTC, datetime

import pytest

from caracal.news.protocol import NewsItem
from caracal.storage.duckdb import DuckDBStorage


@pytest.fixture
def storage():
    """In-memory DuckDB storage for news tests."""
    s = DuckDBStorage(":memory:")
    yield s
    s.close()


@pytest.fixture
def sample_items() -> list[NewsItem]:
    """Sample news items for testing."""
    return [
        NewsItem(
            id="urn:newsml:reuters.com:20260315:1",
            source="reuters",
            feed="business",
            headline="Markets rally on trade deal hopes",
            summary="Global markets surged on optimism.",
            url="https://reuters.com/article/1",
            published_at=datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC),
        ),
        NewsItem(
            id="urn:newsml:reuters.com:20260315:2",
            source="reuters",
            feed="markets",
            headline="Fed holds rates steady",
            summary="The Federal Reserve kept rates unchanged.",
            url="https://reuters.com/article/2",
            published_at=datetime(2026, 3, 15, 11, 0, 0, tzinfo=UTC),
        ),
        NewsItem(
            id="urn:newsml:reuters.com:20260315:3",
            source="reuters",
            feed="tech",
            headline="AI chip demand surges",
            summary=None,
            url="https://reuters.com/article/3",
            published_at=datetime(2026, 3, 15, 12, 0, 0, tzinfo=UTC),
        ),
    ]

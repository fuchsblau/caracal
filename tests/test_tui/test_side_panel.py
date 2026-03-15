"""Tests for SidePanel and NewsItemWidget."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from caracal.config import CaracalConfig
from caracal.news.protocol import NewsItem
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui import CaracalApp
from caracal.tui.data import DataService
from caracal.tui.widgets.news_item import NewsItemWidget
from caracal.tui.widgets.side_panel import SidePanel


def _make_news_item(
    id: str = "1",
    headline: str = "Test headline",
    feed: str = "markets",
    url: str | None = "https://example.com",
    published_at: datetime | None = None,
) -> NewsItem:
    return NewsItem(
        id=id,
        source="reuters",
        feed=feed,
        headline=headline,
        summary=None,
        url=url,
        published_at=published_at or datetime.now(),
    )


def _make_app_with_news(news_count: int = 3) -> CaracalApp:
    """Build a CaracalApp with news items in the DB."""
    config = CaracalConfig(db_path=":memory:")
    storage = DuckDBStorage(":memory:")
    storage.create_watchlist("tech")
    storage.add_to_watchlist("tech", "AAPL")

    from datetime import date

    import pandas as pd

    rows = []
    for i in range(31):
        d = date.today() - timedelta(days=30 - i)
        rows.append(
            {
                "date": d,
                "open": 170 + i * 0.1,
                "high": 172 + i * 0.1,
                "low": 168 + i * 0.1,
                "close": 171 + i * 0.1,
                "volume": 1000000,
            }
        )
    storage.store_ohlcv("AAPL", pd.DataFrame(rows))

    if news_count > 0:
        news_items = [
            _make_news_item(
                id=str(i),
                headline=f"News headline {i}",
                feed="markets",
                url=f"https://example.com/{i}",
                published_at=datetime.now() - timedelta(hours=i),
            )
            for i in range(news_count)
        ]
        storage.store_news(news_items)

    data_service = DataService(config, storage=storage)
    return CaracalApp(config=config, data_service=data_service)


# ---------------------------------------------------------------------------
# SidePanel
# ---------------------------------------------------------------------------


class TestSidePanel:
    @pytest.mark.asyncio
    async def test_side_panel_visible(self):
        app = _make_app_with_news()
        async with app.run_test():
            side = app.query_one(SidePanel)
            assert side.display

    @pytest.mark.asyncio
    async def test_side_panel_has_news_title(self):
        app = _make_app_with_news()
        async with app.run_test():
            side = app.query_one(SidePanel)
            title = side.query_one("#news-title")
            assert title is not None

    @pytest.mark.asyncio
    async def test_side_panel_loads_news(self):
        app = _make_app_with_news(news_count=3)
        async with app.run_test():
            side = app.query_one(SidePanel)
            items = side.query(NewsItemWidget)
            assert len(items) == 3

    @pytest.mark.asyncio
    async def test_side_panel_no_news(self):
        app = _make_app_with_news(news_count=0)
        async with app.run_test():
            side = app.query_one(SidePanel)
            items = side.query(NewsItemWidget)
            assert len(items) == 0

    @pytest.mark.asyncio
    async def test_side_panel_max_50_items(self):
        """Even if more than 50 items exist, only 50 are shown."""
        app = _make_app_with_news(news_count=0)
        async with app.run_test():
            side = app.query_one(SidePanel)
            # Manually load more than 50 items
            items = [
                {
                    "headline": f"News {i}",
                    "feed": "markets",
                    "url": None,
                    "time_ago": "1h",
                }
                for i in range(60)
            ]
            side.load_news(items)
            widgets = side.query(NewsItemWidget)
            assert len(widgets) == 50

    @pytest.mark.asyncio
    async def test_side_panel_scrollable(self):
        """News scroll container exists for scrollability."""
        app = _make_app_with_news()
        async with app.run_test():
            side = app.query_one(SidePanel)
            scroll = side.query_one("#news-scroll")
            assert scroll is not None


# ---------------------------------------------------------------------------
# NewsItemWidget
# ---------------------------------------------------------------------------


class TestNewsItemWidget:
    @pytest.mark.asyncio
    async def test_news_item_stores_url(self):
        app = _make_app_with_news(news_count=1)
        async with app.run_test():
            side = app.query_one(SidePanel)
            items = side.query(NewsItemWidget)
            assert len(items) == 1
            assert items.first().url == "https://example.com/0"

    @pytest.mark.asyncio
    async def test_news_item_stores_headline(self):
        app = _make_app_with_news(news_count=1)
        async with app.run_test():
            side = app.query_one(SidePanel)
            item = side.query(NewsItemWidget).first()
            assert item.headline == "News headline 0"

    @pytest.mark.asyncio
    async def test_news_item_stores_feed(self):
        app = _make_app_with_news(news_count=1)
        async with app.run_test():
            side = app.query_one(SidePanel)
            item = side.query(NewsItemWidget).first()
            assert item.feed == "markets"

    @pytest.mark.asyncio
    async def test_news_item_open_url(self):
        """Enter on focused news item opens URL in browser."""
        app = _make_app_with_news(news_count=1)
        async with app.run_test() as pilot:
            side = app.query_one(SidePanel)
            item = side.query(NewsItemWidget).first()
            item.focus()
            await pilot.pause()
            with patch("caracal.tui.widgets.news_item.webbrowser.open") as mock_open:
                await pilot.press("enter")
                await pilot.pause()
                mock_open.assert_called_once_with("https://example.com/0")

    @pytest.mark.asyncio
    async def test_news_item_open_url_none(self):
        """Enter on news item with no URL does nothing."""
        app = _make_app_with_news(news_count=0)
        async with app.run_test():
            side = app.query_one(SidePanel)
            side.load_news(
                [
                    {
                        "headline": "No URL",
                        "feed": "test",
                        "url": None,
                        "time_ago": "1h",
                    }
                ]
            )
            item = side.query(NewsItemWidget).first()
            with patch("caracal.tui.widgets.news_item.webbrowser.open") as mock_open:
                item.action_open_url()
                mock_open.assert_not_called()


# ---------------------------------------------------------------------------
# News keybinding
# ---------------------------------------------------------------------------


class TestNewsBinding:
    def test_n_binding_registered(self):
        """n key for news focus is registered."""
        keys = {b.key for b in CaracalApp.BINDINGS}
        assert "n" in keys, "Missing n binding for news focus"

    @pytest.mark.asyncio
    async def test_n_key_focuses_news(self):
        """Pressing n moves focus to the news panel."""
        app = _make_app_with_news(news_count=3)
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            focused = app.focused
            assert isinstance(focused, NewsItemWidget)

    @pytest.mark.asyncio
    async def test_n_key_empty_news_focuses_side_panel(self):
        """Pressing n with no news focuses the side panel itself."""
        app = _make_app_with_news(news_count=0)
        async with app.run_test() as pilot:
            await pilot.press("n")
            await pilot.pause()
            focused = app.focused
            assert isinstance(focused, SidePanel)

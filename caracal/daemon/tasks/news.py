"""Daemon task: fetch news from RSS feeds."""

from __future__ import annotations

import asyncio
import logging

from caracal.daemon.registry import TaskContext, TaskResult
from caracal.news.reuters import ReutersRSSSource

logger = logging.getLogger("caracal.daemon")


class NewsFetchTask:
    """Fetch news from RSS sources and store in DuckDB."""

    name = "news"

    async def run(self, context: TaskContext) -> TaskResult:
        source = ReutersRSSSource()

        try:
            items = await asyncio.to_thread(source.fetch)
        except Exception as e:
            logger.error("News fetch failed: %s", e)
            return TaskResult(status="error", message=str(e))

        if not items:
            return TaskResult(status="ok", message="No news items", items_processed=0)

        try:
            new_count = context.db.store_news(items)
        except Exception as e:
            logger.error("Failed to store news: %s", e)
            return TaskResult(status="error", message=str(e))

        logger.info("News fetch: %d new items (of %d total)", new_count, len(items))
        return TaskResult(status="ok", items_processed=new_count)

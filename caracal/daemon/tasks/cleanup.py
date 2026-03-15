"""Daemon task: clean up old news items based on retention policy."""

from __future__ import annotations

import logging

from caracal.daemon.registry import TaskContext, TaskResult

logger = logging.getLogger("caracal.daemon")


class CleanupTask:
    """Delete news items older than the configured retention period."""

    name = "cleanup"

    async def run(self, context: TaskContext) -> TaskResult:
        retention_days = context.config.worker.retention_days

        try:
            deleted = context.db.delete_old_news(retention_days)
        except Exception as e:
            logger.error("Cleanup failed: %s", e)
            return TaskResult(status="error", message=str(e))

        logger.info(
            "Cleanup: deleted %d news items older than %d days",
            deleted,
            retention_days,
        )
        return TaskResult(status="ok", items_processed=deleted)

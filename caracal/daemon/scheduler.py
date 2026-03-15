"""Async scheduler loop for daemon tasks."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from caracal.daemon.registry import TaskContext, TaskRegistry, TaskResult

logger = logging.getLogger("caracal.daemon")

RETRY_DELAY_SECONDS = 300  # 5 minutes


async def scheduler_loop(
    registry: TaskRegistry,
    context: TaskContext,
    retry_delay_seconds: int = RETRY_DELAY_SECONDS,
    on_event: Callable[[dict], Awaitable[None]] | None = None,
) -> None:
    """Run tasks on schedule. Loops forever until cancelled.

    On task failure: logs error, schedules 1 retry after retry_delay_seconds.
    Retry failure: logs error, no further retry.
    Other tasks are not affected by failures.
    """
    retries: dict[str, datetime] = {}
    retried: set[str] = set()  # Track which tasks already had their retry

    while True:
        now = datetime.now()
        name, wait = registry.next_due(now=now, retries=retries)

        await asyncio.sleep(wait)

        is_retry = name in retries
        if is_retry:
            del retries[name]

        task = registry.get_task(name)
        result = await _execute_task(task, context)
        registry.record_run(name, result)
        _persist_run(context, name, result)

        if result.status == "error" and not is_retry:
            retry_at = datetime.now() + timedelta(seconds=retry_delay_seconds)
            retries[name] = retry_at
            retried.add(name)
            logger.warning(
                "Task %s failed: %s — retry in %ds",
                name,
                result.message,
                retry_delay_seconds,
            )
            if on_event is not None:
                await on_event({"type": "error", "task": name, "msg": result.message})
        elif result.status == "error" and is_retry:
            logger.error(
                "Task %s retry failed: %s — no further retry",
                name,
                result.message,
            )
            if on_event is not None:
                await on_event({"type": "error", "task": name, "msg": result.message})
        elif result.status == "ok":
            retried.discard(name)
            logger.info("Task %s completed: %d items", name, result.items_processed)
            if on_event is not None:
                await on_event(
                    {
                        "type": "task_complete",
                        "task": name,
                        "items": result.items_processed,
                    }
                )


async def _execute_task(task, context: TaskContext) -> TaskResult:
    """Execute a task, catching unexpected exceptions."""
    try:
        return await task.run(context)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("Task %s raised unexpected exception", task.name)
        return TaskResult(status="error", message=str(e))


def _persist_run(context: TaskContext, name: str, result: TaskResult) -> None:
    """Store run result in worker_runs table."""
    now = datetime.now()
    try:
        context.db.store_worker_run(
            task_name=name,
            started_at=now,
            completed_at=now,
            status=result.status,
            message=result.message,
            items_processed=result.items_processed,
        )
    except Exception:
        logger.exception("Failed to persist worker run for %s", name)

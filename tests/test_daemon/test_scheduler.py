"""Tests for the daemon scheduler loop."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

import pytest

from caracal.config import CaracalConfig
from caracal.daemon.registry import (
    IntervalTrigger,
    TaskContext,
    TaskRegistry,
    TaskResult,
)
from caracal.daemon.scheduler import scheduler_loop
from caracal.storage.duckdb import DuckDBStorage


@dataclass
class CountingTask:
    """Task that counts invocations."""

    name: str
    call_count: int = 0
    fail_on: list[int] = field(default_factory=list)

    async def run(self, context: TaskContext) -> TaskResult:
        self.call_count += 1
        if self.call_count in self.fail_on:
            return TaskResult(status="error", message="deliberate failure")
        return TaskResult(status="ok", items_processed=1)


@dataclass
class CancelAfterNTask:
    """Task that cancels the scheduler after N runs."""

    name: str
    cancel_after: int
    call_count: int = 0

    async def run(self, context: TaskContext) -> TaskResult:
        self.call_count += 1
        if self.call_count >= self.cancel_after:
            raise asyncio.CancelledError
        return TaskResult(status="ok", items_processed=1)


@pytest.fixture
def context():
    storage = DuckDBStorage(":memory:")
    ctx = TaskContext(db=storage, config=CaracalConfig())
    yield ctx
    storage.close()


class TestSchedulerLoop:
    @pytest.mark.asyncio
    async def test_runs_due_task(self, context):
        task = CancelAfterNTask(name="test", cancel_after=1)
        registry = TaskRegistry()
        registry.register(task, IntervalTrigger(minutes=0))

        with pytest.raises(asyncio.CancelledError):
            await scheduler_loop(registry, context)

        assert task.call_count == 1

    @pytest.mark.asyncio
    async def test_records_run_in_db(self, context):
        task = CancelAfterNTask(name="test", cancel_after=2)
        registry = TaskRegistry()
        registry.register(task, IntervalTrigger(minutes=0))

        with pytest.raises(asyncio.CancelledError):
            await scheduler_loop(registry, context)

        runs = context.db.get_recent_worker_runs()
        assert len(runs) >= 1
        assert runs[0]["task_name"] == "test"
        assert runs[0]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_failed_task_schedules_retry(self, context):
        task = CountingTask(name="flaky", fail_on=[1])
        registry = TaskRegistry()
        registry.register(task, IntervalTrigger(minutes=60))

        # Run with timeout — task fails, retry scheduled in 5min
        # We can't wait 5min, so we just verify the task ran and check DB
        async def run_with_timeout():
            await asyncio.wait_for(
                scheduler_loop(registry, context), timeout=0.5
            )

        with pytest.raises(asyncio.TimeoutError):
            await run_with_timeout()

        assert task.call_count == 1
        runs = context.db.get_recent_worker_runs()
        assert runs[0]["status"] == "error"

    @pytest.mark.asyncio
    async def test_retry_runs_after_delay(self, context):
        # Task fails on first call, succeeds on second (retry)
        task = CountingTask(name="flaky", fail_on=[1])
        registry = TaskRegistry()
        # Use 0-minute interval so it's immediately due
        registry.register(task, IntervalTrigger(minutes=0))

        async def run_briefly():
            await asyncio.wait_for(
                scheduler_loop(registry, context, retry_delay_seconds=0),
                timeout=0.5,
            )

        with pytest.raises(asyncio.TimeoutError):
            await run_briefly()

        # Should have run at least twice: initial failure + retry
        assert task.call_count >= 2
        runs = context.db.get_recent_worker_runs()
        # Most recent should be "ok" (the retry succeeded)
        ok_runs = [r for r in runs if r["status"] == "ok"]
        assert len(ok_runs) >= 1

    @pytest.mark.asyncio
    async def test_no_double_retry(self, context):
        # Task fails on ALL calls — should only retry once
        @dataclass
        class AlwaysFailTask:
            name: str = "always_fail"

            async def run(self, ctx: TaskContext) -> TaskResult:
                return TaskResult(status="error", message="fail")

        task = AlwaysFailTask()
        registry = TaskRegistry()
        registry.register(task, IntervalTrigger(minutes=60))

        async def run_briefly():
            await asyncio.wait_for(
                scheduler_loop(registry, context, retry_delay_seconds=0),
                timeout=0.5,
            )

        with pytest.raises(asyncio.TimeoutError):
            await run_briefly()

        error_runs = [
            r for r in context.db.get_recent_worker_runs() if r["status"] == "error"
        ]
        # Initial failure + retry failure = 2
        assert len(error_runs) == 2

"""Tests for daemon task registry."""

from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest


from caracal.daemon.registry import (
    CronTrigger,
    IntervalTrigger,
    Task,
    TaskContext,
    TaskRegistry,
    TaskResult,
)


class TestCronTrigger:
    def test_seconds_until_next(self):
        # "every day at 02:00"
        trigger = CronTrigger("0 2 * * *")
        now = datetime(2026, 3, 12, 1, 0, 0)
        seconds = trigger.seconds_until_next(now)
        assert seconds == 3600.0  # 1 hour until 02:00

    def test_seconds_until_next_already_passed_today(self):
        trigger = CronTrigger("0 2 * * *")
        now = datetime(2026, 3, 12, 3, 0, 0)
        seconds = trigger.seconds_until_next(now)
        # Next fire is tomorrow at 02:00 = 23 hours
        assert seconds == pytest.approx(23 * 3600, abs=1)

    def test_next_fire_time(self):
        trigger = CronTrigger("0 2 * * *")
        now = datetime(2026, 3, 12, 1, 0, 0)
        next_time = trigger.next_fire_time(now)
        assert next_time == datetime(2026, 3, 12, 2, 0, 0)

    def test_weekday_only_cron(self):
        # "Mon-Fri at 02:00"
        trigger = CronTrigger("0 2 * * 1-5")
        # Saturday at 01:00
        now = datetime(2026, 3, 14, 1, 0, 0)  # Saturday
        next_time = trigger.next_fire_time(now)
        # Next weekday is Monday
        assert next_time.weekday() == 0  # Monday


class TestIntervalTrigger:
    def test_first_run_immediate(self):
        trigger = IntervalTrigger(minutes=5)
        seconds = trigger.seconds_until_next(last_run=None)
        assert seconds == 0.0

    def test_not_yet_due(self):
        trigger = IntervalTrigger(minutes=5)
        last_run = datetime(2026, 3, 12, 10, 0, 0)
        now = datetime(2026, 3, 12, 10, 2, 0)  # 2 min later
        seconds = trigger.seconds_until_next(last_run=last_run, now=now)
        assert seconds == pytest.approx(180.0, abs=1)  # 3 min remaining

    def test_overdue(self):
        trigger = IntervalTrigger(minutes=5)
        last_run = datetime(2026, 3, 12, 10, 0, 0)
        now = datetime(2026, 3, 12, 10, 10, 0)  # 10 min later
        seconds = trigger.seconds_until_next(last_run=last_run, now=now)
        assert seconds == 0.0


class TestTaskResult:
    def test_ok_result(self):
        r = TaskResult(status="ok", items_processed=5)
        assert r.status == "ok"
        assert r.message is None
        assert r.items_processed == 5

    def test_error_result(self):
        r = TaskResult(status="error", message="Network timeout")
        assert r.status == "error"
        assert r.items_processed == 0


@dataclass
class MockTask:
    """Simple mock task for testing."""

    name: str
    _call_count: int = 0

    async def run(self, context: TaskContext) -> TaskResult:
        self._call_count += 1
        return TaskResult(status="ok", items_processed=1)


class TestTaskRegistry:
    def test_register_and_list(self):
        registry = TaskRegistry()
        task = MockTask(name="test")
        trigger = IntervalTrigger(minutes=5)
        registry.register(task, trigger)

        assert len(registry.task_names) == 1
        assert "test" in registry.task_names

    def test_get_task(self):
        registry = TaskRegistry()
        task = MockTask(name="test")
        registry.register(task, IntervalTrigger(minutes=5))

        retrieved = registry.get_task("test")
        assert retrieved is task

    def test_get_task_unknown_raises(self):
        registry = TaskRegistry()
        with pytest.raises(KeyError):
            registry.get_task("nonexistent")

    def test_next_due_interval_first_run(self):
        registry = TaskRegistry()
        registry.register(MockTask(name="a"), IntervalTrigger(minutes=5))
        registry.register(MockTask(name="b"), IntervalTrigger(minutes=10))

        now = datetime(2026, 3, 12, 10, 0, 0)
        name, wait = registry.next_due(now=now)
        # Both are due immediately (no last_run), first registered wins
        assert wait == 0.0

    def test_next_due_after_run(self):
        registry = TaskRegistry()
        registry.register(MockTask(name="fast"), IntervalTrigger(minutes=1))
        registry.register(MockTask(name="slow"), IntervalTrigger(minutes=60))

        now = datetime(2026, 3, 12, 10, 0, 0)
        registry.record_run("fast", TaskResult(status="ok"), now)
        registry.record_run("slow", TaskResult(status="ok"), now)

        check_at = datetime(2026, 3, 12, 10, 0, 30)  # 30s later
        name, wait = registry.next_due(now=check_at)
        assert name == "fast"
        assert wait == pytest.approx(30.0, abs=1)

    def test_next_due_with_retries(self):
        registry = TaskRegistry()
        registry.register(MockTask(name="task"), IntervalTrigger(minutes=60))

        now = datetime(2026, 3, 12, 10, 0, 0)
        registry.record_run("task", TaskResult(status="ok"), now)

        retry_at = datetime(2026, 3, 12, 10, 5, 0)
        retries = {"task": retry_at}

        check_at = datetime(2026, 3, 12, 10, 3, 0)  # 3 min in
        name, wait = registry.next_due(now=check_at, retries=retries)
        assert name == "task"
        assert wait == pytest.approx(120.0, abs=1)  # 2 min until retry

    def test_record_run(self):
        registry = TaskRegistry()
        registry.register(MockTask(name="test"), IntervalTrigger(minutes=5))

        now = datetime(2026, 3, 12, 10, 0, 0)
        result = TaskResult(status="ok", items_processed=3)
        registry.record_run("test", result, now)

        assert registry.last_run("test") == now
        assert registry.last_result("test") is result

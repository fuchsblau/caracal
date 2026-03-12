"""Tests for daemon task registry."""

from datetime import datetime, timedelta

import pytest
from croniter import croniter

from caracal.daemon.registry import (
    CronTrigger,
    IntervalTrigger,
    TaskContext,
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

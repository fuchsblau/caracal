"""Task registry with scheduling support."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

from cronsim import CronSim

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage


@dataclass
class TaskContext:
    """Context passed to every task run."""

    db: DuckDBStorage
    config: CaracalConfig


@dataclass
class TaskResult:
    """Result of a single task execution."""

    status: Literal["ok", "error"]
    message: str | None = None
    items_processed: int = 0


class Task(Protocol):
    """Interface for daemon tasks."""

    @property
    def name(self) -> str: ...

    async def run(self, context: TaskContext) -> TaskResult: ...


@dataclass
class CronTrigger:
    """Cron-based trigger (e.g. '0 2 * * 1-5')."""

    expression: str

    def next_fire_time(self, after: datetime) -> datetime:
        return next(CronSim(self.expression, after))

    def seconds_until_next(self, after: datetime) -> float:
        next_time = self.next_fire_time(after)
        return (next_time - after).total_seconds()


@dataclass
class IntervalTrigger:
    """Interval-based trigger (every N minutes)."""

    minutes: int

    def seconds_until_next(
        self, last_run: datetime | None = None, now: datetime | None = None
    ) -> float:
        if last_run is None:
            return 0.0
        now = now or datetime.now()
        elapsed = (now - last_run).total_seconds()
        remaining = self.minutes * 60 - elapsed
        return max(0.0, remaining)


Trigger = CronTrigger | IntervalTrigger


class TaskRegistry:
    """Registry of tasks with their triggers and run history."""

    def __init__(self) -> None:
        self._tasks: dict[str, tuple[Task, Trigger]] = {}
        self._last_runs: dict[str, datetime] = {}
        self._last_results: dict[str, TaskResult] = {}

    def register(self, task: Task, trigger: Trigger) -> None:
        self._tasks[task.name] = (task, trigger)

    def get_task(self, name: str) -> Task:
        if name not in self._tasks:
            raise KeyError(f"Unknown task: {name}")
        return self._tasks[name][0]

    @property
    def task_names(self) -> list[str]:
        return list(self._tasks.keys())

    def next_due(
        self,
        now: datetime | None = None,
        retries: dict[str, datetime] | None = None,
    ) -> tuple[str, float]:
        """Find the next task to run and seconds until it's due.

        Returns (task_name, seconds_to_wait). Considers both scheduled
        tasks and pending retries.
        """
        now = now or datetime.now()
        candidates: list[tuple[str, float]] = []

        for name, (_, trigger) in self._tasks.items():
            if isinstance(trigger, CronTrigger):
                last = self._last_runs.get(name, now)
                seconds = trigger.seconds_until_next(last)
            else:
                seconds = trigger.seconds_until_next(
                    last_run=self._last_runs.get(name), now=now
                )
            candidates.append((name, seconds))

        if retries:
            for name, retry_at in retries.items():
                seconds = max(0.0, (retry_at - now).total_seconds())
                candidates.append((name, seconds))

        candidates.sort(key=lambda c: c[1])
        return candidates[0]

    def record_run(
        self, name: str, result: TaskResult, at: datetime | None = None
    ) -> None:
        at = at or datetime.now()
        self._last_runs[name] = at
        self._last_results[name] = result

    def last_run(self, name: str) -> datetime | None:
        return self._last_runs.get(name)

    def last_result(self, name: str) -> TaskResult | None:
        return self._last_results.get(name)

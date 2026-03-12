"""Task registry with scheduling support."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

from croniter import croniter

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
        cron = croniter(self.expression, after)
        return cron.get_next(datetime)

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

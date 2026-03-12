"""Tests for worker_runs storage."""

from datetime import datetime

from caracal.storage.duckdb import DuckDBStorage


class TestWorkerRuns:
    def test_store_and_retrieve(self, storage):
        started = datetime(2026, 3, 12, 2, 0, 0)
        completed = datetime(2026, 3, 12, 2, 1, 30)

        storage.store_worker_run(
            task_name="fetch",
            started_at=started,
            completed_at=completed,
            status="ok",
            message=None,
            items_processed=5,
        )

        runs = storage.get_recent_worker_runs(limit=10)
        assert len(runs) == 1
        assert runs[0]["task_name"] == "fetch"
        assert runs[0]["status"] == "ok"
        assert runs[0]["items_processed"] == 5

    def test_recent_runs_ordering(self, storage):
        for i in range(3):
            storage.store_worker_run(
                task_name="fetch",
                started_at=datetime(2026, 3, 12, i, 0, 0),
                completed_at=datetime(2026, 3, 12, i, 1, 0),
                status="ok",
                message=None,
                items_processed=i,
            )

        runs = storage.get_recent_worker_runs(limit=2)
        assert len(runs) == 2
        # Most recent first
        assert runs[0]["items_processed"] == 2
        assert runs[1]["items_processed"] == 1

    def test_store_error_run(self, storage):
        storage.store_worker_run(
            task_name="fetch",
            started_at=datetime(2026, 3, 12, 2, 0, 0),
            completed_at=datetime(2026, 3, 12, 2, 0, 5),
            status="error",
            message="Network timeout",
            items_processed=0,
        )

        runs = storage.get_recent_worker_runs(limit=10)
        assert runs[0]["status"] == "error"
        assert runs[0]["message"] == "Network timeout"

    def test_get_last_run_for_task(self, storage):
        storage.store_worker_run(
            task_name="fetch",
            started_at=datetime(2026, 3, 12, 2, 0, 0),
            completed_at=datetime(2026, 3, 12, 2, 1, 0),
            status="ok",
            message=None,
            items_processed=5,
        )
        storage.store_worker_run(
            task_name="analysis",
            started_at=datetime(2026, 3, 12, 3, 0, 0),
            completed_at=datetime(2026, 3, 12, 3, 2, 0),
            status="ok",
            message=None,
            items_processed=3,
        )

        last = storage.get_last_worker_run("fetch")
        assert last is not None
        assert last["task_name"] == "fetch"

        missing = storage.get_last_worker_run("nonexistent")
        assert missing is None

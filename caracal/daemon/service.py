"""Daemon lifecycle management."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from collections.abc import Awaitable, Callable
from pathlib import Path

from caracal.config import CONFIG_DIR, CaracalConfig
from caracal.daemon.ipc import IPCServer
from caracal.daemon.registry import (
    CronTrigger,
    TaskContext,
    TaskRegistry,
    TaskResult,
)
from caracal.daemon.scheduler import scheduler_loop
from caracal.daemon.tasks.analysis import AnalysisTask
from caracal.daemon.tasks.fetch import FetchTask
from caracal.storage.duckdb import DuckDBStorage

logger = logging.getLogger("caracal.daemon")


class DaemonError(Exception):
    pass


class DaemonAlreadyRunningError(DaemonError):
    pass


class DaemonNotRunningError(DaemonError):
    pass


class DaemonService:
    """Manages daemon lifecycle: start, stop, status, run-once."""

    def __init__(
        self,
        config: CaracalConfig,
        pid_dir: Path | None = None,
        socket_path: Path | None = None,
    ) -> None:
        self._config = config
        self._pid_dir = pid_dir or CONFIG_DIR
        self._pid_path = self._pid_dir / "caracal.pid"
        self._socket_path = socket_path or self._pid_dir / "caracal.sock"
        self._scheduler_task: asyncio.Task | None = None
        self._ipc_server: IPCServer | None = None

    def _build_registry(self) -> TaskRegistry:
        registry = TaskRegistry()
        worker = self._config.worker
        registry.register(FetchTask(), CronTrigger(worker.fetch_schedule))
        registry.register(AnalysisTask(), CronTrigger(worker.analysis_schedule))
        return registry

    # -- PID file management ---

    def _write_pid(self) -> None:
        self._pid_dir.mkdir(parents=True, exist_ok=True)
        self._pid_path.write_text(str(os.getpid()))

    def _remove_pid(self) -> None:
        self._pid_path.unlink(missing_ok=True)

    def _check_not_running(self) -> None:
        if not self._pid_path.exists():
            return
        pid = int(self._pid_path.read_text().strip())
        try:
            os.kill(pid, 0)
            raise DaemonAlreadyRunningError(f"Daemon already running (PID {pid})")
        except ProcessLookupError:
            logger.info("Removing stale PID file (PID %d)", pid)
            self._pid_path.unlink(missing_ok=True)

    # -- Lifecycle ---

    async def start(self) -> None:
        """Start the daemon in foreground. Blocks until stopped."""
        self._check_not_running()
        self._write_pid()

        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGTERM, self._handle_shutdown)
        loop.add_signal_handler(signal.SIGINT, self._handle_shutdown)

        registry = self._build_registry()
        storage = DuckDBStorage(self._config.db_path)
        context = TaskContext(db=storage, config=self._config)

        # Start IPC server
        self._ipc_server = IPCServer(
            socket_path=self._socket_path,
            context=context,
            run_tasks_callback=self._make_run_tasks_callback(registry, context),
        )
        await self._ipc_server.start()

        logger.info(
            "Daemon started (PID %d), %d tasks registered",
            os.getpid(),
            len(registry.task_names),
        )

        self._scheduler_task = asyncio.create_task(
            scheduler_loop(registry, context, on_event=self._ipc_server.broadcast)
        )

        try:
            await self._scheduler_task
        except asyncio.CancelledError:
            logger.info("Daemon stopped")
        finally:
            # Cleanup order per NF-025: IPC → scheduler → DB → PID
            if self._ipc_server is not None:
                await self._ipc_server.shutdown()
            self._remove_pid()
            storage.close()

    def _handle_shutdown(self) -> None:
        logger.info("Received shutdown signal")
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()

    def _make_run_tasks_callback(
        self, registry: TaskRegistry, context: TaskContext
    ) -> Callable[[], Awaitable[None]]:
        """Create a callback for running all tasks immediately (used by IPC refresh)."""

        async def _run_all_tasks() -> None:
            for name in registry.task_names:
                task = registry.get_task(name)
                logger.info("IPC refresh: running task %s", name)
                result = await task.run(context)
                registry.record_run(name, result)
                if self._ipc_server is not None:
                    if result.status == "ok":
                        await self._ipc_server.broadcast(
                            {
                                "type": "task_complete",
                                "task": name,
                                "items": result.items_processed,
                            }
                        )
                    else:
                        await self._ipc_server.broadcast(
                            {
                                "type": "error",
                                "task": name,
                                "msg": result.message,
                            }
                        )

        return _run_all_tasks

    async def run_once(self) -> list[TaskResult]:
        """Run all registered tasks once and return results."""
        registry = self._build_registry()
        storage = DuckDBStorage(self._config.db_path)
        context = TaskContext(db=storage, config=self._config)

        results: list[TaskResult] = []
        try:
            for name in registry.task_names:
                task = registry.get_task(name)
                logger.info("Running task: %s", name)
                result = await task.run(context)
                registry.record_run(name, result)
                results.append(result)
                logger.info(
                    "Task %s: %s (%d items)",
                    name,
                    result.status,
                    result.items_processed,
                )
        finally:
            storage.close()

        return results

    # -- Static operations (don't need a running instance) ---

    @staticmethod
    def stop(pid_dir: Path | None = None) -> None:
        """Send SIGTERM to the running daemon."""
        pid_dir = pid_dir or CONFIG_DIR
        pid_path = pid_dir / "caracal.pid"
        if not pid_path.exists():
            raise DaemonNotRunningError("Daemon is not running (no PID file)")

        pid = int(pid_path.read_text().strip())
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pid_path.unlink(missing_ok=True)
            raise DaemonNotRunningError("Daemon is not running (stale PID file)")

    @staticmethod
    def get_status(config: CaracalConfig, pid_dir: Path | None = None) -> dict:
        """Check daemon status and recent runs."""
        pid_dir = pid_dir or CONFIG_DIR
        pid_path = pid_dir / "caracal.pid"
        running = False
        pid = None

        if pid_path.exists():
            pid = int(pid_path.read_text().strip())
            try:
                os.kill(pid, 0)
                running = True
            except ProcessLookupError:
                pid = None

        recent_runs = []
        try:
            storage = DuckDBStorage(config.db_path)
            recent_runs = storage.get_recent_worker_runs(limit=10)
            storage.close()
        except Exception:
            pass

        socket_path = pid_dir / "caracal.sock"
        return {
            "running": running,
            "pid": pid if running else None,
            "socket_path": str(socket_path),
            "recent_runs": recent_runs,
        }

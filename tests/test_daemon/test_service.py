"""Tests for the DaemonService lifecycle."""

import asyncio
import os
import signal

import pytest

from caracal.config import CaracalConfig
from caracal.daemon.service import DaemonNotRunningError, DaemonService


@pytest.fixture
def config(tmp_path):
    return CaracalConfig(db_path=str(tmp_path / "test.db"))


@pytest.fixture
def pid_dir(tmp_path):
    return tmp_path


class TestPIDFile:
    def test_write_and_read_pid(self, config, pid_dir):
        service = DaemonService(config, pid_dir=pid_dir)
        service._write_pid()

        pid_file = pid_dir / "caracal.pid"
        assert pid_file.exists()
        assert int(pid_file.read_text().strip()) == os.getpid()

    def test_remove_pid(self, config, pid_dir):
        service = DaemonService(config, pid_dir=pid_dir)
        service._write_pid()
        service._remove_pid()

        assert not (pid_dir / "caracal.pid").exists()

    def test_check_not_running_with_no_pid_file(self, config, pid_dir):
        service = DaemonService(config, pid_dir=pid_dir)
        # Should not raise
        service._check_not_running()

    def test_check_not_running_with_stale_pid(self, config, pid_dir):
        pid_file = pid_dir / "caracal.pid"
        pid_file.write_text("999999999")  # Non-existent PID
        service = DaemonService(config, pid_dir=pid_dir)
        # Should clean up stale PID and not raise
        service._check_not_running()
        assert not pid_file.exists()


class TestRunOnce:
    @pytest.mark.asyncio
    async def test_run_once_no_tickers(self, config, pid_dir):
        from unittest.mock import patch

        service = DaemonService(config, pid_dir=pid_dir)
        with patch("caracal.daemon.tasks.news.ReutersRSSSource") as mock_src:
            mock_src.return_value.fetch.return_value = []
            results = await service.run_once()
        # Should run all data tasks (fetch, analysis, news) but with 0 items
        assert len(results) == 3
        for r in results:
            assert r.status == "ok"
            assert r.items_processed == 0

    @pytest.mark.asyncio
    async def test_run_once_excludes_cleanup(self, config, pid_dir):
        """AC3: run_once must NOT execute the cleanup task."""
        service = DaemonService(config, pid_dir=pid_dir)
        registry = service._build_registry(include_maintenance=False)
        assert "cleanup" not in registry.task_names

    def test_full_registry_includes_cleanup(self, config, pid_dir):
        """The full daemon registry includes the cleanup task."""
        service = DaemonService(config, pid_dir=pid_dir)
        registry = service._build_registry(include_maintenance=True)
        assert "cleanup" in registry.task_names


class TestPIDFilePermissions:
    def test_pid_file_has_restrictive_permissions(self, config, pid_dir):
        service = DaemonService(config, pid_dir=pid_dir)
        service._write_pid()

        pid_file = pid_dir / "caracal.pid"
        mode = pid_file.stat().st_mode & 0o777
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"


class TestStop:
    def test_stop_no_pid_file_raises(self, pid_dir):
        with pytest.raises(DaemonNotRunningError):
            DaemonService.stop(pid_dir=pid_dir)

    def test_stop_stale_pid_raises(self, pid_dir):
        pid_file = pid_dir / "caracal.pid"
        pid_file.write_text("999999999")
        with pytest.raises(DaemonNotRunningError):
            DaemonService.stop(pid_dir=pid_dir)
        assert not pid_file.exists()  # cleaned up


class TestStatus:
    def test_status_not_running(self, config, pid_dir):
        info = DaemonService.get_status(config, pid_dir=pid_dir)
        assert info["running"] is False
        assert info["pid"] is None

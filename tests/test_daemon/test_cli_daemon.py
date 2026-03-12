"""Tests for the daemon CLI commands."""

import os
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from caracal.cli import cli


class TestDaemonCLI:
    def test_daemon_group_exists(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["daemon", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output
        assert "stop" in result.output
        assert "status" in result.output
        assert "run-once" in result.output

    def test_daemon_status_not_running(self, tmp_path):
        runner = CliRunner()
        with patch("caracal.cli.daemon_cmd.CONFIG_DIR", tmp_path):
            result = runner.invoke(cli, ["daemon", "status"])
        assert result.exit_code == 0
        assert "not running" in result.output.lower()

    def test_daemon_stop_not_running(self, tmp_path):
        runner = CliRunner()
        with patch("caracal.cli.daemon_cmd.CONFIG_DIR", tmp_path):
            result = runner.invoke(cli, ["daemon", "stop"])
        assert result.exit_code == 1
        assert "not running" in result.output.lower()

    def test_daemon_run_once(self, tmp_path):
        runner = CliRunner()
        db_path = str(tmp_path / "test.db")

        with patch("caracal.config.CONFIG_PATH", tmp_path / "config.toml"):
            config_file = tmp_path / "config.toml"
            config_file.write_text(f'db_path = "{db_path}"\n')
            result = runner.invoke(cli, ["daemon", "run-once"])

        assert result.exit_code == 0

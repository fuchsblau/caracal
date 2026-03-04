"""Tests for caracal init command."""

import json
import tomllib
from unittest.mock import patch

from click.testing import CliRunner

from caracal.cli import cli


class TestInitCommand:
    def test_init_creates_config_file(self, tmp_path):
        config_dir = tmp_path / ".caracal"
        config_file = config_dir / "config.toml"
        with (
            patch("caracal.config.CONFIG_DIR", config_dir),
            patch("caracal.config.CONFIG_PATH", config_file),
            patch("caracal.cli.init.CONFIG_DIR", config_dir),
            patch("caracal.cli.init.CONFIG_PATH", config_file),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            assert config_file.exists()
            parsed = tomllib.loads(config_file.read_text())
            assert "db_path" in parsed

    def test_init_does_not_overwrite_existing(self, tmp_path):
        config_dir = tmp_path / ".caracal"
        config_file = config_dir / "config.toml"
        config_dir.mkdir()
        config_file.write_text('default_period = "6mo"\n')
        with (
            patch("caracal.config.CONFIG_DIR", config_dir),
            patch("caracal.config.CONFIG_PATH", config_file),
            patch("caracal.cli.init.CONFIG_DIR", config_dir),
            patch("caracal.cli.init.CONFIG_PATH", config_file),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            assert "already exists" in result.output.lower()
            assert "6mo" in config_file.read_text()

    def test_init_force_overwrites(self, tmp_path):
        config_dir = tmp_path / ".caracal"
        config_file = config_dir / "config.toml"
        config_dir.mkdir()
        config_file.write_text('default_period = "6mo"\n')
        with (
            patch("caracal.config.CONFIG_DIR", config_dir),
            patch("caracal.config.CONFIG_PATH", config_file),
            patch("caracal.cli.init.CONFIG_DIR", config_dir),
            patch("caracal.cli.init.CONFIG_PATH", config_file),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["init", "--force"])
            assert result.exit_code == 0
            parsed = tomllib.loads(config_file.read_text())
            assert parsed["default_period"] == "1y"

    def test_init_human_output(self, tmp_path):
        config_dir = tmp_path / ".caracal"
        config_file = config_dir / "config.toml"
        with (
            patch("caracal.config.CONFIG_DIR", config_dir),
            patch("caracal.config.CONFIG_PATH", config_file),
            patch("caracal.cli.init.CONFIG_DIR", config_dir),
            patch("caracal.cli.init.CONFIG_PATH", config_file),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            assert "initialized" in result.output.lower()

    def test_init_json_output(self, tmp_path):
        config_dir = tmp_path / ".caracal"
        config_file = config_dir / "config.toml"
        with (
            patch("caracal.config.CONFIG_DIR", config_dir),
            patch("caracal.config.CONFIG_PATH", config_file),
            patch("caracal.cli.init.CONFIG_DIR", config_dir),
            patch("caracal.cli.init.CONFIG_PATH", config_file),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["--format", "json", "init"])
            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert parsed["status"] == "success"
            assert "config_file" in parsed["data"]

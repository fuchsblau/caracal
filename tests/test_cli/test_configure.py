"""Tests for caracal configure command."""

import tomllib
from unittest.mock import patch

from click.testing import CliRunner

from caracal.cli import cli


class TestConfigureCommand:
    def test_configure_creates_config_if_missing(self, tmp_path):
        config_dir = tmp_path / ".caracal"
        config_file = config_dir / "config.toml"
        with (
            patch("caracal.config.CONFIG_DIR", config_dir),
            patch("caracal.config.CONFIG_PATH", config_file),
            patch("caracal.cli.configure.CONFIG_DIR", config_dir),
            patch("caracal.cli.configure.CONFIG_PATH", config_file),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["configure"], input="\n\n\n\n")
            assert result.exit_code == 0
            assert config_file.exists()

    def test_configure_changes_values(self, tmp_path):
        config_dir = tmp_path / ".caracal"
        config_file = config_dir / "config.toml"
        config_dir.mkdir()
        with (
            patch("caracal.config.CONFIG_DIR", config_dir),
            patch("caracal.config.CONFIG_PATH", config_file),
            patch("caracal.cli.configure.CONFIG_DIR", config_dir),
            patch("caracal.cli.configure.CONFIG_PATH", config_file),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["configure"], input="\n6mo\n\n\n")
            assert result.exit_code == 0
            parsed = tomllib.loads(config_file.read_text())
            assert parsed["default_period"] == "6mo"

    def test_configure_shows_current_values(self, tmp_path):
        config_dir = tmp_path / ".caracal"
        config_file = config_dir / "config.toml"
        config_dir.mkdir()
        config_file.write_text('default_period = "3mo"\n')
        with (
            patch("caracal.config.CONFIG_DIR", config_dir),
            patch("caracal.config.CONFIG_PATH", config_file),
            patch("caracal.cli.configure.CONFIG_DIR", config_dir),
            patch("caracal.cli.configure.CONFIG_PATH", config_file),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["configure"], input="\n\n\n\n")
            assert result.exit_code == 0
            assert "3mo" in result.output

    def test_configure_preserves_unchanged_values(self, tmp_path):
        config_dir = tmp_path / ".caracal"
        config_file = config_dir / "config.toml"
        config_dir.mkdir()
        config_file.write_text('default_period = "3mo"\ndefault_format = "json"\n')
        with (
            patch("caracal.config.CONFIG_DIR", config_dir),
            patch("caracal.config.CONFIG_PATH", config_file),
            patch("caracal.cli.configure.CONFIG_DIR", config_dir),
            patch("caracal.cli.configure.CONFIG_PATH", config_file),
        ):
            runner = CliRunner()
            result = runner.invoke(cli, ["configure"], input="\n\n\n\n")
            assert result.exit_code == 0
            parsed = tomllib.loads(config_file.read_text())
            assert parsed["default_period"] == "3mo"
            assert parsed["default_format"] == "json"

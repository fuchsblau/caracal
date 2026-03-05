"""Tests for 'caracal tui' CLI command."""

from unittest.mock import patch

from click.testing import CliRunner

from caracal.cli import cli


class TestTuiCommand:
    def test_tui_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["tui", "--help"])
        assert result.exit_code == 0
        assert "Launch interactive TUI" in result.output

    def test_tui_missing_textual_shows_error(self):
        runner = CliRunner()
        with patch(
            "caracal.cli.tui._launch_tui",
            side_effect=ImportError("No module named 'textual'"),
        ):
            result = runner.invoke(cli, ["tui"])
            assert result.exit_code != 0
            assert "pip install caracal-trading[tui]" in result.output

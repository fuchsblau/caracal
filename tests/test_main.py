"""Smoke test for python -m caracal."""

from click.testing import CliRunner

from caracal.cli import cli


def test_module_entry_point():
    """Running the CLI should not crash."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output

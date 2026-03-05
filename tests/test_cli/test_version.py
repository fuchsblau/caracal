from click.testing import CliRunner

from caracal import __version__
from caracal.cli import cli


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_help_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Automated stock analysis" in result.output

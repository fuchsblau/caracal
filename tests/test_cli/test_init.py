import json
from unittest.mock import patch

from click.testing import CliRunner

from caracal.cli import cli


class TestInitCommand:
    def test_init_creates_directory(self, tmp_path):
        config_dir = tmp_path / ".caracal"
        with patch("caracal.cli.init.CONFIG_DIR", config_dir):
            runner = CliRunner()
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            assert config_dir.exists()

    def test_init_already_exists(self, tmp_path):
        config_dir = tmp_path / ".caracal"
        config_dir.mkdir()
        with patch("caracal.cli.init.CONFIG_DIR", config_dir):
            runner = CliRunner()
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0

    def test_init_human_output(self, tmp_path):
        config_dir = tmp_path / ".caracal"
        with patch("caracal.cli.init.CONFIG_DIR", config_dir):
            runner = CliRunner()
            result = runner.invoke(cli, ["init"])
            assert result.exit_code == 0
            assert "Caracal initialized" in result.output
            assert "Config directory:" in result.output
            assert "Database:" in result.output

    def test_init_json_output(self, tmp_path):
        config_dir = tmp_path / ".caracal"
        with patch("caracal.cli.init.CONFIG_DIR", config_dir):
            runner = CliRunner()
            result = runner.invoke(cli, ["--format", "json", "init"])
            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert parsed["status"] == "success"
            assert "config_dir" in parsed["data"]
            assert "db_path" in parsed["data"]

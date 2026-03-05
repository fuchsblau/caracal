import json
from datetime import date
from unittest.mock import patch

from click.testing import CliRunner

from caracal.cli import cli
from caracal.providers.types import ProviderError


class TestFetchCommand:
    @patch("caracal.cli.fetch.get_provider")
    @patch("caracal.cli.fetch.get_storage")
    def test_fetch_human_output(
        self, mock_get_storage, mock_get_provider, mock_provider, memory_storage
    ):
        mock_get_provider.return_value = mock_provider
        mock_get_storage.return_value = memory_storage

        runner = CliRunner()
        result = runner.invoke(cli, ["fetch", "AAPL"])
        assert result.exit_code == 0
        assert "AAPL" in result.output

    @patch("caracal.cli.fetch.get_provider")
    @patch("caracal.cli.fetch.get_storage")
    def test_fetch_json_output(
        self, mock_get_storage, mock_get_provider, mock_provider, memory_storage
    ):
        mock_get_provider.return_value = mock_provider
        mock_get_storage.return_value = memory_storage

        runner = CliRunner()
        result = runner.invoke(cli, ["--format", "json", "fetch", "AAPL"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["status"] == "success"

    @patch("caracal.cli.fetch.get_provider")
    @patch("caracal.cli.fetch.get_storage")
    def test_fetch_invalid_ticker(
        self, mock_get_storage, mock_get_provider, memory_storage
    ):
        from caracal.providers.types import TickerNotFoundError

        mock_get_provider.return_value.fetch_ohlcv.side_effect = TickerNotFoundError(
            "INVALID"
        )
        mock_get_storage.return_value = memory_storage

        runner = CliRunner()
        result = runner.invoke(cli, ["--format", "json", "fetch", "INVALID"])
        assert result.exit_code == 2
        parsed = json.loads(result.output)
        assert parsed["status"] == "error"

    @patch("caracal.cli.fetch.get_provider")
    @patch("caracal.cli.fetch.get_storage")
    def test_fetch_already_up_to_date(
        self, mock_get_storage, mock_get_provider, mock_provider, memory_storage
    ):
        """Delta-fetch returns rows_added=0 and ticker when up to date."""
        mock_get_provider.return_value = mock_provider
        mock_get_storage.return_value = memory_storage

        # First fetch stores data
        runner = CliRunner()
        result = runner.invoke(cli, ["fetch", "AAPL"])
        assert result.exit_code == 0

        # Mock get_latest_date to return today so start_date > end_date
        memory_storage.get_latest_date = lambda ticker: date.today()

        # Second fetch should hit the "already up to date" path
        result = runner.invoke(cli, ["fetch", "AAPL"])
        assert result.exit_code == 0
        assert "Already up to date" in result.output
        assert "AAPL" in result.output

    @patch("caracal.cli.fetch.get_provider")
    @patch("caracal.cli.fetch.get_storage")
    def test_fetch_provider_error_exit_code(
        self, mock_get_storage, mock_get_provider, memory_storage
    ):
        """ProviderError results in exit code 1."""
        mock_get_provider.return_value.fetch_ohlcv.side_effect = ProviderError(
            "API rate limit exceeded"
        )
        mock_get_storage.return_value = memory_storage

        runner = CliRunner()
        result = runner.invoke(cli, ["fetch", "AAPL"])
        assert result.exit_code == 1

    @patch("caracal.cli.fetch.get_provider")
    @patch("caracal.cli.fetch.get_storage")
    def test_fetch_with_provider_option(
        self, mock_get_storage, mock_get_provider, mock_provider, memory_storage
    ):
        """Test that --provider option is accepted."""
        mock_get_provider.return_value = mock_provider
        mock_get_storage.return_value = memory_storage
        runner = CliRunner()
        result = runner.invoke(cli, ["fetch", "--provider", "yahoo", "AAPL"])
        assert result.exit_code == 0

    @patch("caracal.cli.fetch.get_storage")
    def test_fetch_unknown_provider(self, mock_get_storage, memory_storage):
        """Unknown provider gives an error."""
        mock_get_storage.return_value = memory_storage
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--format", "json", "fetch", "--provider", "nonexistent", "AAPL"]
        )
        assert result.exit_code == 1

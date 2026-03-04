"""Tests for watchlist CLI commands."""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from click.testing import CliRunner

from caracal.cli import cli
from caracal.storage.duckdb import DuckDBStorage


@pytest.fixture
def tmp_storage(tmp_path):
    """File-based DuckDB storage that survives close/reopen cycles."""
    db_path = str(tmp_path / "test.db")
    s = DuckDBStorage(db_path)
    s.close()
    return db_path


def _make_storage(db_path):
    """Create a patched get_storage that uses a temp file path."""
    return lambda *args, **kwargs: DuckDBStorage(db_path)


class TestWatchlistCreate:
    @patch("caracal.cli.watchlist.get_storage")
    def test_create_human(self, mock_get_storage, memory_storage):
        mock_get_storage.return_value = memory_storage
        runner = CliRunner()
        result = runner.invoke(cli, ["watchlist", "create", "tech"])
        assert result.exit_code == 0
        assert "tech" in result.output

    @patch("caracal.cli.watchlist.get_storage")
    def test_create_json(self, mock_get_storage, memory_storage):
        mock_get_storage.return_value = memory_storage
        runner = CliRunner()
        result = runner.invoke(cli, ["--format", "json", "watchlist", "create", "tech"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["status"] == "success"
        assert parsed["data"]["watchlist"] == "tech"

    def test_create_duplicate_error(self, tmp_storage):
        runner = CliRunner()
        with patch(
            "caracal.cli.watchlist.get_storage",
            side_effect=_make_storage(tmp_storage),
        ):
            runner.invoke(cli, ["watchlist", "create", "tech"])
            result = runner.invoke(
                cli, ["--format", "json", "watchlist", "create", "tech"]
            )
        assert result.exit_code == 1
        parsed = json.loads(result.output)
        assert parsed["status"] == "error"


class TestWatchlistDelete:
    def test_delete_human(self, tmp_storage):
        runner = CliRunner()
        with patch(
            "caracal.cli.watchlist.get_storage",
            side_effect=_make_storage(tmp_storage),
        ):
            runner.invoke(cli, ["watchlist", "create", "tech"])
            result = runner.invoke(cli, ["watchlist", "delete", "tech"])
        assert result.exit_code == 0
        assert "tech" in result.output

    @patch("caracal.cli.watchlist.get_storage")
    def test_delete_nonexistent_error(self, mock_get_storage, memory_storage):
        mock_get_storage.return_value = memory_storage
        runner = CliRunner()
        result = runner.invoke(cli, ["--format", "json", "watchlist", "delete", "nope"])
        assert result.exit_code == 1
        parsed = json.loads(result.output)
        assert parsed["status"] == "error"


class TestWatchlistAdd:
    def test_add_single_ticker(self, tmp_storage):
        runner = CliRunner()
        with patch(
            "caracal.cli.watchlist.get_storage",
            side_effect=_make_storage(tmp_storage),
        ):
            runner.invoke(cli, ["watchlist", "create", "tech"])
            result = runner.invoke(cli, ["watchlist", "add", "tech", "AAPL"])
        assert result.exit_code == 0
        assert "AAPL" in result.output

    def test_add_multiple_tickers(self, tmp_storage):
        runner = CliRunner()
        with patch(
            "caracal.cli.watchlist.get_storage",
            side_effect=_make_storage(tmp_storage),
        ):
            runner.invoke(cli, ["watchlist", "create", "tech"])
            result = runner.invoke(cli, ["watchlist", "add", "tech", "AAPL", "MSFT"])
        assert result.exit_code == 0
        assert "AAPL" in result.output
        assert "MSFT" in result.output

    def test_add_json_output(self, tmp_storage):
        runner = CliRunner()
        with patch(
            "caracal.cli.watchlist.get_storage",
            side_effect=_make_storage(tmp_storage),
        ):
            runner.invoke(cli, ["watchlist", "create", "tech"])
            result = runner.invoke(
                cli, ["--format", "json", "watchlist", "add", "tech", "AAPL"]
            )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["status"] == "success"


class TestWatchlistRemove:
    def test_remove_ticker(self, tmp_storage):
        runner = CliRunner()
        with patch(
            "caracal.cli.watchlist.get_storage",
            side_effect=_make_storage(tmp_storage),
        ):
            runner.invoke(cli, ["watchlist", "create", "tech"])
            runner.invoke(cli, ["watchlist", "add", "tech", "AAPL"])
            result = runner.invoke(cli, ["watchlist", "remove", "tech", "AAPL"])
        assert result.exit_code == 0
        assert "AAPL" in result.output

    @patch("caracal.cli.watchlist.get_storage")
    def test_remove_nonexistent_error(self, mock_get_storage, memory_storage):
        mock_get_storage.return_value = memory_storage
        runner = CliRunner()
        runner.invoke(cli, ["watchlist", "create", "tech"])
        result = runner.invoke(
            cli, ["--format", "json", "watchlist", "remove", "tech", "AAPL"]
        )
        assert result.exit_code == 1
        parsed = json.loads(result.output)
        assert parsed["status"] == "error"


class TestWatchlistList:
    @patch("caracal.cli.watchlist.get_storage")
    def test_list_empty(self, mock_get_storage, memory_storage):
        mock_get_storage.return_value = memory_storage
        runner = CliRunner()
        result = runner.invoke(cli, ["watchlist", "list"])
        assert result.exit_code == 0
        assert "No watchlists" in result.output

    def test_list_with_watchlists(self, tmp_storage):
        runner = CliRunner()
        with patch(
            "caracal.cli.watchlist.get_storage",
            side_effect=_make_storage(tmp_storage),
        ):
            runner.invoke(cli, ["watchlist", "create", "tech"])
            runner.invoke(cli, ["watchlist", "add", "tech", "AAPL"])
            result = runner.invoke(cli, ["watchlist", "list"])
        assert result.exit_code == 0
        assert "tech" in result.output

    def test_list_json(self, tmp_storage):
        runner = CliRunner()
        with patch(
            "caracal.cli.watchlist.get_storage",
            side_effect=_make_storage(tmp_storage),
        ):
            runner.invoke(cli, ["watchlist", "create", "tech"])
            result = runner.invoke(cli, ["--format", "json", "watchlist", "list"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["status"] == "success"
        assert len(parsed["data"]["watchlists"]) == 1


class TestWatchlistShow:
    def test_show_with_prices(self, tmp_storage):
        provider = MagicMock()
        provider.fetch_ohlcv.return_value = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 2)],
                "open": [100.0, 101.0],
                "high": [105.0, 106.0],
                "low": [99.0, 100.0],
                "close": [104.0, 105.0],
                "volume": [1000000, 1100000],
            }
        )
        runner = CliRunner()
        with (
            patch(
                "caracal.cli.watchlist.get_storage",
                side_effect=_make_storage(tmp_storage),
            ),
            patch("caracal.cli.watchlist.get_provider", return_value=provider),
        ):
            runner.invoke(cli, ["watchlist", "create", "tech"])
            runner.invoke(cli, ["watchlist", "add", "tech", "AAPL"])
            result = runner.invoke(cli, ["watchlist", "show", "tech"])
        assert result.exit_code == 0
        assert "AAPL" in result.output

    def test_show_json(self, tmp_storage):
        provider = MagicMock()
        provider.fetch_ohlcv.return_value = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 2)],
                "open": [100.0, 101.0],
                "high": [105.0, 106.0],
                "low": [99.0, 100.0],
                "close": [104.0, 105.0],
                "volume": [1000000, 1100000],
            }
        )
        runner = CliRunner()
        with (
            patch(
                "caracal.cli.watchlist.get_storage",
                side_effect=_make_storage(tmp_storage),
            ),
            patch("caracal.cli.watchlist.get_provider", return_value=provider),
        ):
            runner.invoke(cli, ["watchlist", "create", "tech"])
            runner.invoke(cli, ["watchlist", "add", "tech", "AAPL"])
            result = runner.invoke(
                cli, ["--format", "json", "watchlist", "show", "tech"]
            )
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["status"] == "success"

    @patch("caracal.cli.watchlist.get_storage")
    def test_show_nonexistent_error(self, mock_get_storage, memory_storage):
        mock_get_storage.return_value = memory_storage
        runner = CliRunner()
        result = runner.invoke(cli, ["--format", "json", "watchlist", "show", "nope"])
        assert result.exit_code == 1
        parsed = json.loads(result.output)
        assert parsed["status"] == "error"

    def test_show_empty_watchlist(self, tmp_storage):
        runner = CliRunner()
        with patch(
            "caracal.cli.watchlist.get_storage",
            side_effect=_make_storage(tmp_storage),
        ):
            runner.invoke(cli, ["watchlist", "create", "tech"])
            result = runner.invoke(cli, ["watchlist", "show", "tech"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "no tickers" in result.output.lower()

import json
from datetime import date, timedelta
from unittest.mock import patch

import pandas as pd
import pytest
from click.testing import CliRunner

from caracal.cli import cli


@pytest.fixture
def stored_analysis_data(memory_storage):
    n = 60
    df = pd.DataFrame(
        {
            "date": [date(2024, 1, 1) + timedelta(days=i) for i in range(n)],
            "open": [100.0 + i * 0.5 for i in range(n)],
            "high": [101.0 + i * 0.5 for i in range(n)],
            "low": [99.0 + i * 0.5 for i in range(n)],
            "close": [100.0 + i * 0.5 for i in range(n)],
            "volume": [1000000] * n,
        }
    )
    memory_storage.store_ohlcv("AAPL", df)
    return memory_storage


class TestEntryCommand:
    @patch("caracal.cli.entry.get_storage")
    def test_entry_json(self, mock_get_storage, stored_analysis_data):
        mock_get_storage.return_value = stored_analysis_data
        runner = CliRunner()
        result = runner.invoke(cli, ["--format", "json", "entry", "AAPL"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["status"] == "success"
        assert parsed["data"]["signal"] in ("buy", "sell", "hold")
        assert 0.0 <= parsed["data"]["confidence"] <= 1.0

    @patch("caracal.cli.entry.get_storage")
    def test_entry_no_data(self, mock_get_storage, memory_storage):
        mock_get_storage.return_value = memory_storage
        runner = CliRunner()
        result = runner.invoke(cli, ["--format", "json", "entry", "UNKNOWN"])
        assert result.exit_code == 2

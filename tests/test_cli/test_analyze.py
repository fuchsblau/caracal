import json
from datetime import date, timedelta
from unittest.mock import patch

import pandas as pd
import pytest
from click.testing import CliRunner

from caracal.cli import cli


@pytest.fixture
def stored_data(memory_storage):
    """Pre-populate storage with sample data."""
    df = pd.DataFrame(
        {
            "date": [date(2024, 1, 1) + timedelta(days=i) for i in range(30)],
            "open": [100.0 + i for i in range(30)],
            "high": [105.0 + i for i in range(30)],
            "low": [99.0 + i for i in range(30)],
            "close": [104.0 + i for i in range(30)],
            "volume": [1000000] * 30,
        }
    )
    memory_storage.store_ohlcv("AAPL", df)
    return memory_storage


class TestAnalyzeCommand:
    @patch("caracal.cli.analyze.get_storage")
    def test_analyze_json(self, mock_get_storage, stored_data):
        mock_get_storage.return_value = stored_data
        runner = CliRunner()
        result = runner.invoke(cli, ["--format", "json", "analyze", "AAPL"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["status"] == "success"
        assert "indicators" in parsed["data"]

    @patch("caracal.cli.analyze.get_storage")
    def test_analyze_no_data(self, mock_get_storage, memory_storage):
        mock_get_storage.return_value = memory_storage
        runner = CliRunner()
        result = runner.invoke(cli, ["--format", "json", "analyze", "UNKNOWN"])
        assert result.exit_code == 2

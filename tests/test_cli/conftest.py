from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

from caracal.storage.duckdb import DuckDBStorage


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.name = "mock"
    provider.fetch_ohlcv.return_value = pd.DataFrame(
        {
            "date": [date(2024, 1, 2), date(2024, 1, 3)],
            "open": [100.0, 101.0],
            "high": [105.0, 106.0],
            "low": [99.0, 100.0],
            "close": [104.0, 105.0],
            "volume": [1000000, 1100000],
        }
    )
    return provider


@pytest.fixture
def memory_storage():
    s = DuckDBStorage(":memory:")
    yield s
    s.close()

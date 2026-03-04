from datetime import date

import pandas as pd
import pytest


@pytest.fixture
def mock_ohlcv_df():
    """Sample OHLCV DataFrame as returned by a provider."""
    return pd.DataFrame(
        {
            "date": [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)],
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 106.0, 107.0],
            "low": [99.0, 100.0, 101.0],
            "close": [104.0, 105.0, 106.0],
            "volume": [1000000, 1100000, 1200000],
        }
    )

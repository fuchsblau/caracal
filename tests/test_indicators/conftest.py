from datetime import date, timedelta

import pandas as pd
import pytest


@pytest.fixture
def sample_ohlcv():
    """20-day OHLCV data with predictable values."""
    dates = [date(2024, 1, 1) + timedelta(days=i) for i in range(20)]
    closes = [float(100 + i) for i in range(20)]  # 100, 101, ..., 119
    return pd.DataFrame(
        {
            "date": dates,
            "open": closes,
            "high": [c + 2 for c in closes],
            "low": [c - 2 for c in closes],
            "close": closes,
            "volume": [1000000] * 20,
        }
    )

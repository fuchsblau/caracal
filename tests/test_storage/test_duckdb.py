from datetime import date

import pandas as pd


class TestStoreAndGetOHLCV:
    def test_store_and_retrieve(self, storage):
        df = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 2)],
                "open": [100.0, 101.0],
                "high": [105.0, 106.0],
                "low": [99.0, 100.0],
                "close": [104.0, 105.0],
                "volume": [1000, 1100],
            }
        )
        count = storage.store_ohlcv("AAPL", df)
        assert count == 2

        result = storage.get_ohlcv("AAPL")
        assert len(result) == 2
        assert list(result.columns) == [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

    def test_get_empty_ticker(self, storage):
        result = storage.get_ohlcv("UNKNOWN")
        assert len(result) == 0

    def test_upsert_no_duplicates(self, storage):
        df1 = pd.DataFrame(
            {
                "date": [date(2024, 1, 1)],
                "open": [100.0],
                "high": [105.0],
                "low": [99.0],
                "close": [104.0],
                "volume": [1000],
            }
        )
        df2 = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 2)],
                "open": [100.0, 101.0],
                "high": [105.0, 106.0],
                "low": [99.0, 100.0],
                "close": [104.0, 105.0],
                "volume": [1000, 1100],
            }
        )
        storage.store_ohlcv("AAPL", df1)
        storage.store_ohlcv("AAPL", df2)
        result = storage.get_ohlcv("AAPL")
        assert len(result) == 2

    def test_date_range_filter(self, storage):
        df = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)],
                "open": [100.0, 101.0, 102.0],
                "high": [105.0, 106.0, 107.0],
                "low": [99.0, 100.0, 101.0],
                "close": [104.0, 105.0, 106.0],
                "volume": [1000, 1100, 1200],
            }
        )
        storage.store_ohlcv("AAPL", df)
        result = storage.get_ohlcv("AAPL", start_date=date(2024, 1, 2))
        assert len(result) == 2


class TestDeltaFetch:
    def test_latest_date(self, storage):
        df = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 2)],
                "open": [100.0, 101.0],
                "high": [105.0, 106.0],
                "low": [99.0, 100.0],
                "close": [104.0, 105.0],
                "volume": [1000, 1100],
            }
        )
        storage.store_ohlcv("AAPL", df)
        assert storage.get_latest_date("AAPL") == date(2024, 1, 2)

    def test_latest_date_empty(self, storage):
        assert storage.get_latest_date("UNKNOWN") is None


class TestIndicators:
    def test_store_and_get_indicators(self, storage):
        df = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 2)],
                "name": ["sma_20", "sma_20"],
                "value": [100.5, 101.0],
            }
        )
        count = storage.store_indicators("AAPL", df)
        assert count == 2

        result = storage.get_indicators("AAPL")
        assert len(result) == 2

    def test_get_indicators_by_name(self, storage):
        df = pd.DataFrame(
            {
                "date": [date(2024, 1, 1), date(2024, 1, 1)],
                "name": ["sma_20", "rsi_14"],
                "value": [100.5, 55.0],
            }
        )
        storage.store_indicators("AAPL", df)
        result = storage.get_indicators("AAPL", names=["rsi_14"])
        assert len(result) == 1
        assert result.iloc[0]["name"] == "rsi_14"

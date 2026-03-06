"""Tests for AnalysisService."""

from datetime import date, timedelta

import pandas as pd
import pytest

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui.services.analysis_service import (
    CATEGORY_ORDER,
    INDICATOR_CATEGORIES,
    INDICATOR_DISPLAY_NAMES,
    AnalysisService,
)


def _store_ohlcv(storage, ticker, days=31, trend="flat"):
    """Store synthetic OHLCV data for testing."""
    base_price = 100.0
    rows = []
    for i in range(days):
        if trend == "up":
            price = base_price + i * 2
        elif trend == "down":
            price = base_price - i * 2
        else:
            price = base_price + (i % 3 - 1)
        d = date.today() - timedelta(days=days - i)
        rows.append({
            "date": d,
            "open": price - 0.5,
            "high": price + 1,
            "low": price - 1,
            "close": price,
            "volume": 1000000,
        })
    df = pd.DataFrame(rows)
    storage.store_ohlcv(ticker, df)


@pytest.fixture
def storage():
    s = DuckDBStorage(":memory:")
    yield s
    s.close()


@pytest.fixture
def service(storage):
    config = CaracalConfig(db_path=":memory:")
    return AnalysisService(config=config, storage=storage)


class TestWatchlistOverview:
    def test_empty_watchlist(self, service, storage):
        storage.create_watchlist("tech")
        rows = service.get_watchlist_overview("tech")
        assert rows == []

    def test_ticker_with_data(self, service, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "AAPL")
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "open": [150.0, 152.0],
            "high": [155.0, 156.0],
            "low": [149.0, 151.0],
            "close": [153.0, 155.0],
            "volume": [1000000, 1100000],
        })
        storage.store_ohlcv("AAPL", df)
        rows = service.get_watchlist_overview("tech")
        assert len(rows) == 1
        assert rows[0]["ticker"] == "AAPL"
        assert rows[0]["close"] == 155.0
        assert rows[0]["change_pct"] is not None

    def test_ticker_no_data(self, service, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "UNKNOWN")
        rows = service.get_watchlist_overview("tech")
        assert len(rows) == 1
        assert rows[0]["close"] is None
        assert rows[0]["signal"] == "N/A"

    def test_indicator_fields_present(self, service, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "AAPL")
        _store_ohlcv(storage, "AAPL", days=31)
        rows = service.get_watchlist_overview("tech")
        row = rows[0]
        assert "confidence" in row
        assert "rsi" in row
        assert "macd_interpretation" in row
        assert "bb_position" in row

    def test_indicator_fields_none_insufficient_data(self, service, storage):
        storage.create_watchlist("tech")
        storage.add_to_watchlist("tech", "NEW")
        _store_ohlcv(storage, "NEW", days=5)
        rows = service.get_watchlist_overview("tech")
        row = rows[0]
        assert row["confidence"] is None
        assert row["rsi"] is None


class TestStockDetail:
    def test_detail_with_data(self, service, storage):
        df = pd.DataFrame({
            "date": pd.to_datetime(
                [f"2024-01-{d:02d}" for d in range(1, 32)]
            ),
            "open": [150.0 + i for i in range(31)],
            "high": [155.0 + i for i in range(31)],
            "low": [149.0 + i for i in range(31)],
            "close": [153.0 + i for i in range(31)],
            "volume": [1000000 + i * 1000 for i in range(31)],
        })
        storage.store_ohlcv("AAPL", df)
        detail = service.get_stock_detail("AAPL")
        assert detail["ticker"] == "AAPL"
        assert detail["close"] is not None
        assert "signal" in detail
        assert "indicators" in detail
        assert "ohlcv" in detail
        assert "indicator_groups" in detail
        assert "vote_counts" in detail

    def test_detail_empty(self, service):
        detail = service.get_stock_detail("UNKNOWN")
        assert detail["ticker"] == "UNKNOWN"
        assert detail["close"] is None
        assert detail["signal"] == "N/A"
        assert detail["indicator_groups"] == []
        assert detail["vote_counts"] is None
        assert detail["ohlcv"] == []

    def test_indicator_groups_ordered(self, service, storage):
        _store_ohlcv(storage, "AAPL", days=60)
        detail = service.get_stock_detail("AAPL")
        categories = [g["category"] for g in detail["indicator_groups"]]
        assert categories == ["Trend", "Momentum", "Volatility"]

    def test_ohlcv_limited_to_5(self, service, storage):
        _store_ohlcv(storage, "AAPL", days=60)
        detail = service.get_stock_detail("AAPL")
        assert len(detail["ohlcv"]) == 5


class TestInterpretIndicator:
    def test_sma_bullish(self, service):
        interp, detail = service._interpret_indicator(
            "sma_20", 170.0, close=175.0, indicators={}
        )
        assert interp == "bullish"
        assert detail == "above"

    def test_sma_bearish(self, service):
        interp, detail = service._interpret_indicator(
            "sma_20", 180.0, close=175.0, indicators={}
        )
        assert interp == "bearish"
        assert detail == "below"

    def test_rsi_overbought(self, service):
        interp, detail = service._interpret_indicator(
            "rsi_14", 72.0, close=175.0, indicators={}
        )
        assert interp == "overbought"

    def test_rsi_oversold(self, service):
        interp, detail = service._interpret_indicator(
            "rsi_14", 28.0, close=175.0, indicators={}
        )
        assert interp == "oversold"

    def test_rsi_neutral(self, service):
        interp, detail = service._interpret_indicator(
            "rsi_14", 50.0, close=175.0, indicators={}
        )
        assert interp == "neutral"

    def test_macd_bullish(self, service):
        interp, detail = service._interpret_indicator(
            "macd", 3.5, close=175.0, indicators={"macd_signal": 2.1}
        )
        assert interp == "bullish"
        assert detail == "bull"

    def test_macd_bearish(self, service):
        interp, detail = service._interpret_indicator(
            "macd", 1.0, close=175.0, indicators={"macd_signal": 2.1}
        )
        assert interp == "bearish"
        assert detail == "bear"

    def test_none_value(self, service):
        interp, detail = service._interpret_indicator(
            "sma_20", None, close=175.0, indicators={}
        )
        assert interp is None
        assert detail is None


class TestCalculateVoteCounts:
    def test_with_sufficient_data(self, service, storage):
        _store_ohlcv(storage, "AAPL", days=60, trend="up")
        df = storage.get_ohlcv("AAPL")
        counts = service._calculate_vote_counts(df)
        assert counts is not None
        assert "buy" in counts
        assert "hold" in counts
        assert "sell" in counts
        assert "total" in counts
        assert counts["total"] == counts["buy"] + counts["hold"] + counts["sell"]

    def test_with_insufficient_data(self, service, storage):
        _store_ohlcv(storage, "NEW", days=5)
        df = storage.get_ohlcv("NEW")
        counts = service._calculate_vote_counts(df)
        assert counts is None

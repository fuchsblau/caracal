"""Tests for AssetDetailView widget."""

import pytest
from textual.app import App, ComposeResult

from caracal.tui.widgets.asset_detail_view import AssetDetailView

SAMPLE_DETAIL = {
    "ticker": "AAPL",
    "close": 175.50,
    "change_pct": 2.34,
    "signal": "buy",
    "confidence": 0.85,
    "indicators": {
        "sma_20": 170.0,
        "sma_50": 165.0,
        "ema_12": 172.0,
        "rsi_14": 65.2,
        "macd": 3.5,
        "macd_signal": 2.1,
        "bollinger_upper": 180.0,
        "bollinger_lower": 160.0,
    },
    "ohlcv": [
        {"date": "2026-03-04", "open": 174.0, "high": 176.0,
         "low": 173.0, "close": 175.5, "volume": 5000000},
    ],
}


class DetailTestApp(App):
    def __init__(self, detail: dict) -> None:
        super().__init__()
        self._detail = detail

    def compose(self) -> ComposeResult:
        yield AssetDetailView()

    def on_mount(self) -> None:
        view = self.query_one(AssetDetailView)
        view.load_detail(self._detail)


class TestAssetDetailView:
    @pytest.mark.asyncio
    async def test_shows_ticker_in_header(self):
        app = DetailTestApp(SAMPLE_DETAIL)
        async with app.run_test():
            view = app.query_one(AssetDetailView)
            header_text = view.query_one("#detail-header").content
            assert "AAPL" in header_text

    @pytest.mark.asyncio
    async def test_shows_all_indicators(self):
        app = DetailTestApp(SAMPLE_DETAIL)
        async with app.run_test():
            view = app.query_one(AssetDetailView)
            ind_table = view.query_one("#indicators-table")
            assert ind_table.row_count == 8

    @pytest.mark.asyncio
    async def test_shows_ohlcv(self):
        app = DetailTestApp(SAMPLE_DETAIL)
        async with app.run_test():
            view = app.query_one(AssetDetailView)
            ohlcv_table = view.query_one("#ohlcv-table")
            assert ohlcv_table.row_count == 1

    @pytest.mark.asyncio
    async def test_handles_empty_data(self):
        empty = {
            "ticker": "NEW", "close": None, "change_pct": None,
            "signal": "N/A", "confidence": 0.0, "indicators": {}, "ohlcv": [],
        }
        app = DetailTestApp(empty)
        async with app.run_test():
            view = app.query_one(AssetDetailView)
            assert view.query_one("#indicators-table").row_count == 0

"""Tests for AssetDetailView widget."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static

from caracal.tui.widgets.asset_detail_view import AssetDetailView

SAMPLE_DETAIL = {
    "ticker": "AAPL",
    "close": 175.50,
    "change_pct": 2.34,
    "signal": "buy",
    "confidence": 0.85,
    "indicators": {
        "sma_20": 170.0, "sma_50": 165.0, "ema_12": 172.0,
        "rsi_14": 65.2, "macd": 3.5, "macd_signal": 2.1,
        "bollinger_upper": 180.0, "bollinger_lower": 160.0,
    },
    "indicator_groups": [
        {
            "category": "Trend",
            "indicators": [
                {"name": "SMA 20", "key": "sma_20", "value": 170.0,
                 "interpretation": "bullish", "detail": "above"},
                {"name": "SMA 50", "key": "sma_50", "value": 165.0,
                 "interpretation": "bullish", "detail": "above"},
                {"name": "EMA 12", "key": "ema_12", "value": 172.0,
                 "interpretation": "bullish", "detail": "above"},
            ],
        },
        {
            "category": "Momentum",
            "indicators": [
                {"name": "RSI 14", "key": "rsi_14", "value": 65.2,
                 "interpretation": "neutral", "detail": "neutral"},
                {"name": "MACD", "key": "macd", "value": 3.5,
                 "interpretation": "bullish", "detail": "bull"},
                {"name": "MACD Signal", "key": "macd_signal", "value": 2.1,
                 "interpretation": None, "detail": None},
            ],
        },
        {
            "category": "Volatility",
            "indicators": [
                {"name": "BB Upper", "key": "bollinger_upper", "value": 180.0,
                 "interpretation": "neutral", "detail": "in band"},
                {"name": "BB Lower", "key": "bollinger_lower", "value": 160.0,
                 "interpretation": "neutral", "detail": "in band"},
            ],
        },
    ],
    "vote_counts": {"buy": 4, "hold": 1, "sell": 0, "total": 5},
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
            header = app.query_one("#detail-header", Static)
            assert "AAPL" in header.content

    @pytest.mark.asyncio
    async def test_shows_signal_in_header(self):
        app = DetailTestApp(SAMPLE_DETAIL)
        async with app.run_test():
            header = app.query_one("#detail-header", Static)
            assert "BUY" in header.content

    @pytest.mark.asyncio
    async def test_shows_vote_counts_in_header(self):
        app = DetailTestApp(SAMPLE_DETAIL)
        async with app.run_test():
            header = app.query_one("#detail-header", Static)
            content = header.content
            assert "4" in content
            assert "\u25b2" in content

    @pytest.mark.asyncio
    async def test_shows_indicator_sections(self):
        app = DetailTestApp(SAMPLE_DETAIL)
        async with app.run_test():
            sections = app.query_one("#indicator-sections", Static)
            content = sections.content
            assert "Trend" in content
            assert "Momentum" in content
            assert "Volatility" in content

    @pytest.mark.asyncio
    async def test_shows_indicator_values(self):
        app = DetailTestApp(SAMPLE_DETAIL)
        async with app.run_test():
            sections = app.query_one("#indicator-sections", Static)
            content = sections.content
            assert "SMA 20" in content
            assert "170.00" in content

    @pytest.mark.asyncio
    async def test_shows_interpretations(self):
        app = DetailTestApp(SAMPLE_DETAIL)
        async with app.run_test():
            sections = app.query_one("#indicator-sections", Static)
            content = sections.content
            assert "above" in content or "bull" in content

    @pytest.mark.asyncio
    async def test_shows_ohlcv(self):
        app = DetailTestApp(SAMPLE_DETAIL)
        async with app.run_test():
            ohlcv_table = app.query_one("#ohlcv-table")
            assert ohlcv_table.row_count == 1

    @pytest.mark.asyncio
    async def test_handles_empty_data(self):
        empty = {
            "ticker": "NEW", "close": None, "change_pct": None,
            "signal": "N/A", "confidence": 0.0, "indicators": {},
            "indicator_groups": [], "vote_counts": None, "ohlcv": [],
        }
        app = DetailTestApp(empty)
        async with app.run_test():
            assert app.query_one("#ohlcv-table").row_count == 0

    @pytest.mark.asyncio
    async def test_no_vote_counts_when_none(self):
        detail = {**SAMPLE_DETAIL, "vote_counts": None}
        app = DetailTestApp(detail)
        async with app.run_test():
            header = app.query_one("#detail-header", Static)
            assert "AAPL" in header.content

    @pytest.mark.asyncio
    async def test_skips_empty_sections(self):
        detail = {
            **SAMPLE_DETAIL,
            "indicator_groups": [
                {
                    "category": "Trend",
                    "indicators": [
                        {"name": "SMA 20", "key": "sma_20", "value": None,
                         "interpretation": None, "detail": None},
                    ],
                },
                {
                    "category": "Momentum",
                    "indicators": [
                        {"name": "RSI 14", "key": "rsi_14", "value": 65.2,
                         "interpretation": "neutral", "detail": "neutral"},
                    ],
                },
            ],
        }
        app = DetailTestApp(detail)
        async with app.run_test():
            sections = app.query_one("#indicator-sections", Static)
            content = sections.content
            assert "Trend" not in content
            assert "Momentum" in content

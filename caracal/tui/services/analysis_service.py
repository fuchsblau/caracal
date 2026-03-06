"""Analysis and indicator interpretation for TUI screens."""

from __future__ import annotations

import logging

from caracal.analysis.entry_points import calculate_entry_signal
from caracal.config import CaracalConfig
from caracal.output.precision import PERCENT_DECIMALS, PRICE_DECIMALS
from caracal.storage.duckdb import DuckDBStorage

logger = logging.getLogger("caracal")

# -- Indicator Category Registry (ADR-018, NF-022) ----------------------------

INDICATOR_CATEGORIES: dict[str, list[str]] = {
    "Trend": ["sma_20", "sma_50", "ema_12"],
    "Momentum": ["rsi_14", "macd", "macd_signal"],
    "Volatility": ["bollinger_upper", "bollinger_lower"],
}

CATEGORY_ORDER: list[str] = ["Trend", "Momentum", "Volatility"]

INDICATOR_DISPLAY_NAMES: dict[str, str] = {
    "sma_20": "SMA 20",
    "sma_50": "SMA 50",
    "ema_12": "EMA 12",
    "rsi_14": "RSI 14",
    "macd": "MACD",
    "macd_signal": "MACD Signal",
    "bollinger_upper": "BB Upper",
    "bollinger_lower": "BB Lower",
}


def _calculate_change_pct(close: float, prev_close: float) -> float | None:
    """Calculate percentage change between two prices."""
    if prev_close == 0:
        return None
    return round(((close - prev_close) / prev_close) * 100, PERCENT_DECIMALS)


class AnalysisService:
    """Watchlist overview and stock detail analysis -- extracted from DataService."""

    def __init__(self, config: CaracalConfig, storage: DuckDBStorage) -> None:
        self._storage = storage

    def get_watchlist_overview(self, name: str) -> list[dict]:
        """Return overview rows for a watchlist.

        Each row: {ticker, close, change_pct, signal, confidence, rsi,
                   macd_interpretation, bb_position}
        Uses cached OHLCV data from DuckDB -- no provider calls.
        """
        tickers = self._storage.get_watchlist_items(name)
        rows = []
        for ticker in tickers:
            row = self._build_ticker_row(ticker)
            rows.append(row)
        return rows

    def _build_ticker_row(self, ticker: str) -> dict:
        """Build a single watchlist row from cached data."""
        name = self._storage.get_ticker_name(ticker) or ticker
        df = self._storage.get_ohlcv(ticker)

        if df.empty or len(df) < 1:
            return {
                "ticker": ticker,
                "name": name,
                "close": None,
                "change_pct": None,
                "signal": "N/A",
                "confidence": None,
                "rsi": None,
                "macd_interpretation": None,
                "bb_position": None,
            }

        close = round(float(df.iloc[-1]["close"]), PRICE_DECIMALS)
        change_pct = None
        if len(df) >= 2:
            prev_close = float(df.iloc[-2]["close"])
            change_pct = _calculate_change_pct(close, prev_close)

        signal = "N/A"
        confidence = None
        rsi = None
        macd_interpretation = None
        bb_position = None

        if len(df) >= 30:
            result = calculate_entry_signal(df)
            signal = result["signal"]
            confidence = result["confidence"]

            indicators = result["indicators"]

            # RSI value
            rsi_val = indicators.get("rsi_14")
            if rsi_val is not None:
                rsi = round(rsi_val, PERCENT_DECIMALS)

            # MACD interpretation: bullish if MACD > signal line
            macd_val = indicators.get("macd")
            macd_sig = indicators.get("macd_signal")
            if macd_val is not None and macd_sig is not None:
                macd_interpretation = "bull" if macd_val > macd_sig else "bear"

            # Bollinger position: where is price relative to bands
            bb_upper = indicators.get("bollinger_upper")
            bb_lower = indicators.get("bollinger_lower")
            if bb_upper is not None and bb_lower is not None:
                band_width = bb_upper - bb_lower
                if band_width > 0:
                    position = (close - bb_lower) / band_width
                    if position > 1.0:
                        bb_position = "overbought"
                    elif position < 0.0:
                        bb_position = "oversold"
                    else:
                        bb_position = "neutral"

        return {
            "ticker": ticker,
            "name": name,
            "close": close,
            "change_pct": change_pct,
            "signal": signal,
            "confidence": confidence,
            "rsi": rsi,
            "macd_interpretation": macd_interpretation,
            "bb_position": bb_position,
        }

    # -- Indicator interpretation (ADR-018, US-075) ---------------------------

    def _interpret_indicator(
        self, key: str, value: float | None, *, close: float, indicators: dict
    ) -> tuple[str | None, str | None]:
        """Return (interpretation, detail) for an indicator value."""
        if value is None:
            return None, None

        if key in ("sma_20", "sma_50", "ema_12"):
            if close > value:
                return "bullish", "above"
            return "bearish", "below"

        if key == "rsi_14":
            if value > 70:
                return "overbought", "overbought"
            if value < 30:
                return "oversold", "oversold"
            return "neutral", "neutral"

        if key == "macd":
            macd_sig = indicators.get("macd_signal")
            if macd_sig is not None:
                if value > macd_sig:
                    return "bullish", "bull"
                return "bearish", "bear"
            return None, None

        if key == "macd_signal":
            return None, None

        if key in ("bollinger_upper", "bollinger_lower"):
            bb_upper = indicators.get("bollinger_upper")
            bb_lower = indicators.get("bollinger_lower")
            if bb_upper is not None and bb_lower is not None:
                band_width = bb_upper - bb_lower
                if band_width > 0:
                    position = (close - bb_lower) / band_width
                    if position > 1.0:
                        return "overbought", "overbought"
                    if position < 0.0:
                        return "oversold", "oversold"
                    return "neutral", "in band"
            return None, None

        return None, None

    # -- Vote counts (US-076) ------------------------------------------------

    def _calculate_vote_counts(self, df) -> dict | None:
        """Count buy/hold/sell votes from individual rule scores."""
        if len(df) < 30:
            return None
        result = calculate_entry_signal(df, include_scores=True)
        scores = result.get("scores", [])
        if not scores:
            return None
        buy = sum(1 for s in scores if s > 0.2)
        sell = sum(1 for s in scores if s < -0.2)
        hold = sum(1 for s in scores if -0.2 <= s <= 0.2)
        return {"buy": buy, "hold": hold, "sell": sell, "total": len(scores)}

    # -- Stock detail ---------------------------------------------------------

    def get_stock_detail(self, ticker: str) -> dict:
        """Return full detail for a single stock.

        Returns: {ticker, close, change_pct, signal, confidence,
                  indicators, indicator_groups, vote_counts, ohlcv}
        """
        df = self._storage.get_ohlcv(ticker)

        if df.empty:
            return {
                "ticker": ticker,
                "close": None,
                "change_pct": None,
                "signal": "N/A",
                "confidence": 0.0,
                "indicators": {},
                "indicator_groups": [],
                "vote_counts": None,
                "ohlcv": [],
            }

        close = round(float(df.iloc[-1]["close"]), PRICE_DECIMALS)
        change_pct = None
        if len(df) >= 2:
            prev_close = float(df.iloc[-2]["close"])
            change_pct = _calculate_change_pct(close, prev_close)

        result = calculate_entry_signal(df)
        indicators = result["indicators"]

        # Build grouped indicators with interpretations
        indicator_groups = []
        for category in CATEGORY_ORDER:
            keys = INDICATOR_CATEGORIES.get(category, [])
            group_indicators = []
            for key in keys:
                value = indicators.get(key)
                interpretation, detail = self._interpret_indicator(
                    key, value, close=close, indicators=indicators
                )
                group_indicators.append({
                    "name": INDICATOR_DISPLAY_NAMES.get(key, key),
                    "key": key,
                    "value": value,
                    "interpretation": interpretation,
                    "detail": detail,
                })
            indicator_groups.append({
                "category": category,
                "indicators": group_indicators,
            })

        # Vote counts
        vote_counts = self._calculate_vote_counts(df)

        # Last 5 days of OHLCV (US-077)
        tail = df.tail(5)
        ohlcv_rows = []
        for _, row in tail.iterrows():
            ohlcv_rows.append({
                "date": (
                    str(row["date"].date())
                    if hasattr(row["date"], "date")
                    else str(row["date"])
                ),
                "open": round(float(row["open"]), PRICE_DECIMALS),
                "high": round(float(row["high"]), PRICE_DECIMALS),
                "low": round(float(row["low"]), PRICE_DECIMALS),
                "close": round(float(row["close"]), PRICE_DECIMALS),
                "volume": int(row["volume"]),
            })

        return {
            "ticker": ticker,
            "close": close,
            "change_pct": change_pct,
            "signal": result["signal"],
            "confidence": result["confidence"],
            "indicators": indicators,
            "indicator_groups": indicator_groups,
            "vote_counts": vote_counts,
            "ohlcv": ohlcv_rows,
        }

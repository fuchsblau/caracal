"""Daemon task: fetch market data for all watchlist tickers."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from caracal.daemon.registry import TaskContext, TaskResult
from caracal.providers import get_provider as _get_provider

logger = logging.getLogger("caracal.daemon")


def get_provider(config):
    """Build provider from config."""
    name = config.default_provider
    kwargs = {}
    if name in config.providers:
        kwargs = config.providers[name]
    return _get_provider(name, **kwargs)


class FetchTask:
    """Fetch OHLCV data for all tickers in all watchlists."""

    name = "fetch"

    async def run(self, context: TaskContext) -> TaskResult:
        tickers = _collect_tickers(context)
        if not tickers:
            logger.info("No tickers to fetch")
            return TaskResult(status="ok", message="No tickers", items_processed=0)

        try:
            provider = get_provider(context.config)
        except (ValueError, ImportError) as e:
            return TaskResult(status="error", message=str(e))

        processed = 0
        errors: list[str] = []

        for ticker in sorted(tickers):
            try:
                count = await _fetch_ticker(context, provider, ticker)
                processed += 1
                logger.info("Fetched %s: %d rows", ticker, count)
            except Exception as e:
                errors.append(f"{ticker}: {e}")
                logger.error("Failed to fetch %s: %s", ticker, e)

        if errors and processed == 0:
            return TaskResult(
                status="error",
                message="; ".join(errors),
                items_processed=0,
            )

        return TaskResult(status="ok", items_processed=processed)


def _collect_tickers(context: TaskContext) -> set[str]:
    """Collect unique tickers from all watchlists."""
    tickers: set[str] = set()
    for wl in context.db.get_watchlists():
        tickers.update(context.db.get_watchlist_items(wl["name"]))
    return tickers


async def _fetch_ticker(context: TaskContext, provider, ticker: str) -> int:
    """Fetch OHLCV for a single ticker with delta-fetch."""
    end_date = date.today()
    latest = context.db.get_latest_date(ticker)

    if latest:
        start_date = latest + timedelta(days=1)
        if start_date > end_date:
            return 0  # Already up to date
    else:
        period_days = {"1y": 365, "6mo": 182, "3mo": 91, "1mo": 30, "5y": 1825}
        days = period_days.get(context.config.default_period, 365)
        start_date = end_date - timedelta(days=days)

    df = await asyncio.to_thread(provider.fetch_ohlcv, ticker, start_date, end_date)
    return context.db.store_ohlcv(ticker, df)

"""Daemon task: calculate technical indicators for all watchlist tickers."""

from __future__ import annotations

import asyncio
import logging

import pandas as pd

from caracal.analysis.compute import compute_indicators
from caracal.daemon.registry import TaskContext, TaskResult

logger = logging.getLogger("caracal.daemon")


class AnalysisTask:
    """Calculate indicators for all tickers in all watchlists."""

    name = "analysis"

    async def run(self, context: TaskContext) -> TaskResult:
        tickers = _collect_tickers(context)
        if not tickers:
            return TaskResult(status="ok", message="No tickers", items_processed=0)

        processed = 0
        errors: list[str] = []

        for ticker in sorted(tickers):
            try:
                done = await asyncio.to_thread(
                    _analyze_ticker, context, ticker
                )
                if done:
                    processed += 1
            except Exception as e:
                errors.append(f"{ticker}: {e}")
                logger.error("Failed to analyze %s: %s", ticker, e)

        if errors and processed == 0:
            return TaskResult(
                status="error",
                message="; ".join(errors),
                items_processed=0,
            )

        return TaskResult(status="ok", items_processed=processed)


def _collect_tickers(context: TaskContext) -> set[str]:
    tickers: set[str] = set()
    for wl in context.db.get_watchlists():
        tickers.update(context.db.get_watchlist_items(wl["name"]))
    return tickers


def _analyze_ticker(context: TaskContext, ticker: str) -> bool:
    """Compute and store indicators for a single ticker. Returns True if processed."""
    df = context.db.get_ohlcv(ticker)
    if df.empty:
        logger.info("Skipping %s: no OHLCV data", ticker)
        return False

    _, rows = compute_indicators(df)
    if rows:
        ind_df = pd.DataFrame(rows)
        context.db.store_indicators(ticker, ind_df)
        logger.info("Analyzed %s: %d indicator rows", ticker, len(rows))

    return True

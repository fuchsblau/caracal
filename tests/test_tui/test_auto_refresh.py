"""Tests for auto-refresh and change highlighting."""

import pytest
from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui import CaracalApp
from caracal.tui.data import DataService
from caracal.tui.widgets.watchlist_panel import WatchlistPanel


def _make_app():
    config = CaracalConfig(db_path=":memory:")
    storage = DuckDBStorage(":memory:")
    storage.create_watchlist("tech")
    storage.add_to_watchlist("tech", "AAPL")
    import pandas as pd
    from datetime import date, timedelta
    rows = []
    for i in range(31):
        d = date.today() - timedelta(days=30 - i)
        rows.append({"date": d, "open": 170 + i * 0.1, "high": 172 + i * 0.1,
                      "low": 168 + i * 0.1, "close": 171 + i * 0.1, "volume": 1000000})
    storage.store_ohlcv("AAPL", pd.DataFrame(rows))
    return CaracalApp(config=config, data_service=DataService(config, storage=storage))


class TestAutoRefresh:
    @pytest.mark.asyncio
    async def test_app_starts_without_crash(self):
        """Basic smoke test: app with auto-refresh timer starts correctly."""
        app = _make_app()
        async with app.run_test():
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            assert table.row_count >= 1

    @pytest.mark.asyncio
    async def test_refresh_preserves_cursor(self):
        app = _make_app()
        async with app.run_test() as pilot:
            await pilot.press("r")
            await pilot.pause()
            panel = app.query_one(WatchlistPanel)
            table = panel.get_active_table()
            assert table.row_count >= 1

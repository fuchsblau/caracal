"""Tests for InfoScreen."""

import pytest

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui import CaracalApp
from caracal.tui.data import DataService


@pytest.fixture
def app():
    config = CaracalConfig(db_path=":memory:")
    storage = DuckDBStorage(":memory:")
    storage.create_watchlist("test")
    data_service = DataService(config, storage=storage)
    return CaracalApp(config=config, data_service=data_service)


class TestInfoScreen:
    @pytest.mark.asyncio
    async def test_open_and_close_info(self, app):
        async with app.run_test() as pilot:
            await pilot.press("i")
            from caracal.tui.screens.info import InfoScreen
            assert isinstance(app.screen, InfoScreen)

            await pilot.press("escape")
            # Back to main app screen (not InfoScreen)
            assert not isinstance(app.screen, InfoScreen)

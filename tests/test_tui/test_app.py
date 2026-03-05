"""Tests for CaracalApp."""

import pytest

from caracal.config import CaracalConfig


@pytest.fixture
def config():
    return CaracalConfig(db_path=":memory:")


class TestCaracalApp:
    def test_app_creates(self, config):
        from caracal.tui import CaracalApp

        app = CaracalApp(config=config)
        assert app.config == config
        assert app.title == "Caracal"

    @pytest.mark.asyncio
    async def test_app_mounts(self, config):
        from caracal.tui import CaracalApp

        app = CaracalApp(config=config)
        async with app.run_test() as pilot:
            assert app.screen is not None

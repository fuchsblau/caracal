"""Tests for CaracalFooter widget."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Footer

from caracal.tui.widgets.footer import CaracalFooter


class FooterTestApp(App):
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield CaracalFooter()


class TestCaracalFooter:
    @pytest.mark.asyncio
    async def test_is_footer_subclass(self):
        assert issubclass(CaracalFooter, Footer)

    @pytest.mark.asyncio
    async def test_default_timestamp_is_dash(self):
        app = FooterTestApp()
        async with app.run_test():
            footer = app.query_one(CaracalFooter)
            assert footer.last_updated == "—"

    @pytest.mark.asyncio
    async def test_timestamp_updates(self):
        app = FooterTestApp()
        async with app.run_test():
            footer = app.query_one(CaracalFooter)
            footer.last_updated = "2026-03-06 14:32:15"
            assert footer.last_updated == "2026-03-06 14:32:15"

    @pytest.mark.asyncio
    async def test_timestamp_label_present(self):
        app = FooterTestApp()
        async with app.run_test():
            footer = app.query_one(CaracalFooter)
            label = footer.query_one("#update-timestamp")
            assert label is not None

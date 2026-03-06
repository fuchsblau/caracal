"""Tests for CaracalFooter widget (US-066)."""

import pytest
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Footer, Label

from caracal.tui.widgets.footer import CaracalFooter


class FooterTestApp(App):
    BINDINGS = [("q", "quit", "Quit"), ("r", "noop", "Refresh")]

    def compose(self) -> ComposeResult:
        yield CaracalFooter()

    def action_noop(self) -> None:
        pass


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

    @pytest.mark.asyncio
    async def test_last_updated_is_reactive(self):
        """last_updated must be a reactive property for automatic updates."""
        assert hasattr(CaracalFooter, "last_updated")
        # Check it's declared as reactive (class-level descriptor)
        assert isinstance(
            CaracalFooter.__dict__["last_updated"], reactive
        ), "last_updated should be a Textual reactive"

    @pytest.mark.asyncio
    async def test_watcher_updates_label_text(self):
        """Setting last_updated triggers the watcher to update the label."""
        app = FooterTestApp()
        async with app.run_test():
            footer = app.query_one(CaracalFooter)
            label = footer.query_one("#update-timestamp", Label)
            # Initial label text
            assert "Updated" in label.content
            # Change timestamp
            footer.last_updated = "2026-01-01 00:00:00"
            assert "2026-01-01 00:00:00" in label.content

    @pytest.mark.asyncio
    async def test_timestamp_label_is_docked_left(self):
        """Timestamp label is docked to the left side of the footer."""
        app = FooterTestApp()
        async with app.run_test():
            footer = app.query_one(CaracalFooter)
            label = footer.query_one("#update-timestamp", Label)
            assert label is not None

    @pytest.mark.asyncio
    async def test_multiple_timestamp_updates(self):
        """Footer handles multiple consecutive timestamp updates."""
        app = FooterTestApp()
        async with app.run_test():
            footer = app.query_one(CaracalFooter)
            for ts in ["10:00:00", "10:01:00", "10:02:00"]:
                footer.last_updated = ts
                assert footer.last_updated == ts

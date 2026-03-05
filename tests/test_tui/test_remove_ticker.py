"""Tests for RemoveTickerModal."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Label

from caracal.tui.screens.remove_ticker import RemoveTickerModal


class ModalTestApp(App):
    """Minimal app for testing RemoveTickerModal."""

    TICKER = "AAPL"

    def __init__(self) -> None:
        super().__init__()
        self.result: bool | None = "NOT_SET"

    def on_mount(self) -> None:
        self.push_screen(RemoveTickerModal(self.TICKER), self._on_result)

    def _on_result(self, value: bool) -> None:
        self.result = value

    def compose(self) -> ComposeResult:
        return []


@pytest.mark.asyncio
async def test_remove_modal_shows_ticker_name():
    """Modal displays the ticker to remove."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        labels = app.screen.query(Label)
        assert any("AAPL" in str(label.render()) for label in labels)


@pytest.mark.asyncio
async def test_remove_modal_confirm():
    """Clicking Remove button dismisses with True."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        confirm_btn = app.screen.query_one("#confirm-btn", Button)
        await pilot.click(f"#{confirm_btn.id}")
        assert app.result is True


@pytest.mark.asyncio
async def test_remove_modal_cancel_button():
    """Clicking Cancel button dismisses with False."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        cancel_btn = app.screen.query_one("#cancel-btn", Button)
        await pilot.click(f"#{cancel_btn.id}")
        assert app.result is False


@pytest.mark.asyncio
async def test_remove_modal_escape_cancels():
    """Pressing Escape dismisses with False."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await pilot.press("escape")
        assert app.result is False

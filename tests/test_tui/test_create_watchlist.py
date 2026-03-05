"""Tests for CreateWatchlistModal."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input

from caracal.tui.screens.create_watchlist import CreateWatchlistModal


class ModalTestApp(App):
    """Minimal app for testing modals."""

    def __init__(self) -> None:
        super().__init__()
        self.result: str | None = "NOT_SET"

    def on_mount(self) -> None:
        self.push_screen(CreateWatchlistModal(), self._on_result)

    def _on_result(self, value: str | None) -> None:
        self.result = value

    def compose(self) -> ComposeResult:
        return []


@pytest.mark.asyncio
async def test_create_modal_has_input():
    """Modal contains an Input widget."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one(Input)


@pytest.mark.asyncio
async def test_create_modal_submit_name():
    """Entering a name and pressing Enter dismisses with the name."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        input_widget = app.screen.query_one(Input)
        input_widget.value = "my_watchlist"
        await pilot.press("enter")
        assert app.result == "my_watchlist"


@pytest.mark.asyncio
async def test_create_modal_escape_cancels():
    """Pressing Escape dismisses with None."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await pilot.press("escape")
        assert app.result is None


@pytest.mark.asyncio
async def test_create_modal_empty_name_rejected():
    """Submitting empty name shows error, does not dismiss."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await pilot.press("enter")
        # Modal should still be active (not dismissed)
        assert app.result == "NOT_SET"

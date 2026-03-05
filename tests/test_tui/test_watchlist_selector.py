"""Tests for WatchlistSelectorModal."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import OptionList

from caracal.tui.screens.watchlist_selector import WatchlistSelectorModal

SAMPLE_WATCHLISTS = [
    {"name": "crypto", "ticker_count": 3},
    {"name": "etfs", "ticker_count": 8},
    {"name": "tech_stocks", "ticker_count": 5},
]


class ModalTestApp(App):
    """Minimal app for testing modals."""

    def __init__(self, current: str = "tech_stocks") -> None:
        super().__init__()
        self.current = current
        self.result: str | None = "NOT_SET"

    def on_mount(self) -> None:
        self.push_screen(
            WatchlistSelectorModal(SAMPLE_WATCHLISTS, self.current),
            self._on_result,
        )

    def _on_result(self, value: str | None) -> None:
        self.result = value

    def compose(self) -> ComposeResult:
        return []


@pytest.mark.asyncio
async def test_selector_shows_all_watchlists():
    """Selector displays all watchlist names with ticker counts."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        option_list = app.screen.query_one(OptionList)
        assert option_list.option_count == 3


@pytest.mark.asyncio
async def test_selector_enter_selects():
    """Pressing Enter on a highlighted item dismisses with name."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        # First option is "crypto"
        await pilot.press("enter")
        await pilot.pause()
        assert app.result == "crypto"


@pytest.mark.asyncio
async def test_selector_navigate_and_select():
    """Navigate down and select second option."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("down")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert app.result == "etfs"


@pytest.mark.asyncio
async def test_selector_escape_cancels():
    """Pressing Escape dismisses with None."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await pilot.press("escape")
        assert app.result is None

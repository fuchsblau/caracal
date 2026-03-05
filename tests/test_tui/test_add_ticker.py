"""Tests for AddTickerModal."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input

from caracal.tui.screens.add_ticker import AddTickerModal


class ModalTestApp(App):
    """Minimal app for testing AddTickerModal."""

    def __init__(self) -> None:
        super().__init__()
        self.result: list[str] | None = "NOT_SET"

    def on_mount(self) -> None:
        self.push_screen(AddTickerModal(), self._on_result)

    def _on_result(self, value: list[str] | None) -> None:
        self.result = value

    def compose(self) -> ComposeResult:
        return []


@pytest.mark.asyncio
async def test_add_modal_has_input():
    """Modal contains an Input widget."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        assert app.screen.query_one(Input)


@pytest.mark.asyncio
async def test_add_modal_single_ticker():
    """Entering a single ticker dismisses with list of one."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        input_widget = app.screen.query_one(Input)
        input_widget.value = "AAPL"
        await pilot.press("enter")
        assert app.result == ["AAPL"]


@pytest.mark.asyncio
async def test_add_modal_batch_space_separated():
    """Space-separated tickers are parsed as list."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        input_widget = app.screen.query_one(Input)
        input_widget.value = "AAPL MSFT NVDA"
        await pilot.press("enter")
        assert app.result == ["AAPL", "MSFT", "NVDA"]


@pytest.mark.asyncio
async def test_add_modal_batch_comma_separated():
    """Comma-separated tickers are parsed as list."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        input_widget = app.screen.query_one(Input)
        input_widget.value = "AAPL, MSFT, NVDA"
        await pilot.press("enter")
        assert app.result == ["AAPL", "MSFT", "NVDA"]


@pytest.mark.asyncio
async def test_add_modal_dot_tickers_preserved():
    """Tickers with dots (BRK.B, SAP.DE) are not split at dot."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        input_widget = app.screen.query_one(Input)
        input_widget.value = "BRK.B SAP.DE 7203.T"
        await pilot.press("enter")
        assert app.result == ["BRK.B", "SAP.DE", "7203.T"]


@pytest.mark.asyncio
async def test_add_modal_uppercase_normalization():
    """Lowercase input is normalized to uppercase."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        input_widget = app.screen.query_one(Input)
        input_widget.value = "aapl msft"
        await pilot.press("enter")
        assert app.result == ["AAPL", "MSFT"]


@pytest.mark.asyncio
async def test_add_modal_escape_cancels():
    """Pressing Escape dismisses with None."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await pilot.press("escape")
        assert app.result is None


@pytest.mark.asyncio
async def test_add_modal_empty_input_rejected():
    """Submitting empty input shows error, does not dismiss."""
    app = ModalTestApp()
    async with app.run_test() as pilot:
        await pilot.press("enter")
        assert app.result == "NOT_SET"

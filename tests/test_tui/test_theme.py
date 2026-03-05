"""Tests for TUI theme constants."""

from caracal.tui.theme import COLOR_NEGATIVE, COLOR_POSITIVE, COLOR_PRICE, SIGNAL_COLORS


def test_signal_colors_cover_all_signals():
    assert "buy" in SIGNAL_COLORS
    assert "sell" in SIGNAL_COLORS
    assert "hold" in SIGNAL_COLORS


def test_color_constants_are_strings():
    assert isinstance(COLOR_PRICE, str)
    assert isinstance(COLOR_POSITIVE, str)
    assert isinstance(COLOR_NEGATIVE, str)

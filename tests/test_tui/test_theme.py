"""Tests for TUI theme constants and Textual Theme object."""

import pytest
from textual.theme import Theme

from caracal.tui.theme import (
    CARACAL_THEME,
    COLOR_NEGATIVE,
    COLOR_NEUTRAL,
    COLOR_POSITIVE,
    COLOR_PRICE,
    COLOR_WARNING,
    COLOR_OVERBOUGHT,
    COLOR_OVERSOLD,
    INDICATOR_STYLES,
    SIGNAL_COLORS,
    format_bb,
    format_confidence,
    format_macd,
    format_rsi,
)


# -- CARACAL_THEME (Textual Theme object) -------------------------------------

EXPECTED_COLORS = {
    "primary": "#56b6c2",
    "secondary": "#3d8b94",
    "accent": "#c678dd",
    "foreground": "#abb2bf",
    "background": "#1e2127",
    "surface": "#282c34",
    "panel": "#2c313a",
    "warning": "#e5c07b",
    "error": "#e06c75",
    "success": "#98c379",
}


def test_caracal_theme_is_textual_theme():
    assert isinstance(CARACAL_THEME, Theme)


def test_caracal_theme_name_and_mode():
    assert CARACAL_THEME.name == "caracal"
    assert CARACAL_THEME.dark is True


@pytest.mark.parametrize("attr,expected", EXPECTED_COLORS.items())
def test_caracal_theme_color(attr, expected):
    assert getattr(CARACAL_THEME, attr) == expected


def test_signal_colors_cover_all_signals():
    assert "buy" in SIGNAL_COLORS
    assert "sell" in SIGNAL_COLORS
    assert "hold" in SIGNAL_COLORS


def test_color_constants_are_strings():
    assert isinstance(COLOR_PRICE, str)
    assert isinstance(COLOR_POSITIVE, str)
    assert isinstance(COLOR_NEGATIVE, str)


def test_color_constants_match_palette():
    assert COLOR_PRICE == "#56b6c2"
    assert COLOR_POSITIVE == "#98c379"
    assert COLOR_NEGATIVE == "#e06c75"
    assert COLOR_WARNING == "#e5c07b"
    assert COLOR_OVERBOUGHT == "#e06c75"
    assert COLOR_OVERSOLD == "#98c379"
    assert COLOR_NEUTRAL == "#e5c07b"


def test_warning_color_exists():
    assert COLOR_WARNING is not None


def test_indicator_styles_exist():
    assert "overbought" in INDICATOR_STYLES
    assert "oversold" in INDICATOR_STYLES
    assert "neutral" in INDICATOR_STYLES


def test_format_rsi_overbought():
    text = format_rsi(72.4)
    assert "72" in str(text)
    assert text.style is not None


def test_format_rsi_oversold():
    text = format_rsi(28.1)
    assert "28" in str(text)


def test_format_rsi_neutral():
    text = format_rsi(50.3)
    assert "50" in str(text)


def test_format_rsi_none():
    text = format_rsi(None)
    assert "N/A" in str(text)


def test_format_macd_bull():
    text = format_macd("bull")
    assert "BULL" in str(text)


def test_format_macd_bear():
    text = format_macd("bear")
    assert "BEAR" in str(text)


def test_format_macd_none():
    text = format_macd(None)
    assert "N/A" in str(text)


def test_format_bb_overbought():
    text = format_bb("overbought")
    assert "OB" in str(text)


def test_format_bb_oversold():
    text = format_bb("oversold")
    assert "OS" in str(text)


def test_format_bb_neutral():
    text = format_bb("neutral")
    assert "OK" in str(text)


def test_format_confidence_high():
    text = format_confidence(0.85)
    assert "85" in str(text)


def test_format_confidence_low():
    text = format_confidence(0.15)
    assert "15" in str(text)


def test_format_confidence_none():
    text = format_confidence(None)
    assert "N/A" in str(text)

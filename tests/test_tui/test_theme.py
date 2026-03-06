"""Tests for TUI theme constants and Textual Theme object."""

from caracal.tui.theme import (
    CARACAL_THEME,
    COLOR_NEGATIVE,
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


def test_caracal_theme_exists():
    assert CARACAL_THEME is not None


def test_caracal_theme_name():
    assert CARACAL_THEME.name == "caracal"


def test_caracal_theme_dark():
    assert CARACAL_THEME.dark is True


def test_caracal_theme_primary():
    assert CARACAL_THEME.primary == "#56b6c2"


def test_caracal_theme_secondary():
    assert CARACAL_THEME.secondary == "#3d8b94"


def test_caracal_theme_accent():
    assert CARACAL_THEME.accent == "#c678dd"


def test_caracal_theme_foreground():
    assert CARACAL_THEME.foreground == "#abb2bf"


def test_caracal_theme_background():
    assert CARACAL_THEME.background == "#1e2127"


def test_caracal_theme_surface():
    assert CARACAL_THEME.surface == "#282c34"


def test_caracal_theme_panel():
    assert CARACAL_THEME.panel == "#2c313a"


def test_caracal_theme_warning():
    assert CARACAL_THEME.warning == "#e5c07b"


def test_caracal_theme_error():
    assert CARACAL_THEME.error == "#e06c75"


def test_caracal_theme_success():
    assert CARACAL_THEME.success == "#98c379"


def test_signal_colors_cover_all_signals():
    assert "buy" in SIGNAL_COLORS
    assert "sell" in SIGNAL_COLORS
    assert "hold" in SIGNAL_COLORS


def test_color_constants_are_strings():
    assert isinstance(COLOR_PRICE, str)
    assert isinstance(COLOR_POSITIVE, str)
    assert isinstance(COLOR_NEGATIVE, str)


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

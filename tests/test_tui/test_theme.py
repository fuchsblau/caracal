"""Tests for TUI theme constants and Textual Theme object."""

import pytest
from textual.theme import Theme

from caracal.tui.theme import (
    CARACAL_THEME,
    COLOR_MUTED,
    COLOR_NEGATIVE,
    COLOR_NEUTRAL,
    COLOR_POSITIVE,
    COLOR_PRICE,
    COLOR_WARNING,
    COLOR_OVERBOUGHT,
    COLOR_OVERSOLD,
    INDICATOR_STYLES,
    INTERPRETATION_COLORS,
    INTERPRETATION_SYMBOLS,
    SIGNAL_COLORS,
    format_bb,
    format_confidence,
    format_interpretation,
    format_macd,
    format_rsi,
    format_trend,
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


def test_signal_colors_semantic_mapping():
    """US-060: BUY=green, SELL=red, HOLD=yellow."""
    assert SIGNAL_COLORS["buy"] == COLOR_POSITIVE
    assert SIGNAL_COLORS["sell"] == COLOR_NEGATIVE
    assert SIGNAL_COLORS["hold"] == COLOR_NEUTRAL


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


def _style_str(text):
    """Return lowercased style string for assertion helpers."""
    return str(text.style).lower()


# -- format_rsi ---------------------------------------------------------------


class TestFormatRSI:
    """US-060: RSI formatted as 'value arrow' with semantic colors."""

    def test_overbought_content(self):
        text = format_rsi(72.4)
        assert text.plain == "72 \u25b2"

    def test_overbought_color(self):
        text = format_rsi(72.4)
        assert COLOR_OVERBOUGHT.lstrip("#") in _style_str(text)

    def test_oversold_content(self):
        text = format_rsi(28.1)
        assert text.plain == "28 \u25bc"

    def test_oversold_color(self):
        text = format_rsi(28.1)
        assert COLOR_OVERSOLD.lstrip("#") in _style_str(text)

    def test_neutral_content(self):
        text = format_rsi(50.3)
        assert text.plain == "50 \u2014"

    def test_neutral_color(self):
        text = format_rsi(50.3)
        assert COLOR_NEUTRAL.lstrip("#") in _style_str(text)

    def test_none_returns_na(self):
        text = format_rsi(None)
        assert text.plain == "N/A"
        assert "dim" in _style_str(text)

    def test_boundary_above_70(self):
        text = format_rsi(70.1)
        assert "\u25b2" in text.plain

    def test_boundary_at_70(self):
        """RSI exactly 70 is not overbought (>70 threshold)."""
        text = format_rsi(70.0)
        assert "\u2014" in text.plain

    def test_boundary_just_above_30(self):
        """RSI 30.1 is neutral (not oversold)."""
        text = format_rsi(30.1)
        assert "\u2014" in text.plain

    def test_boundary_at_30(self):
        """RSI exactly 30 is not oversold (<30 threshold)."""
        text = format_rsi(30.0)
        assert "\u2014" in text.plain

    def test_right_justified(self):
        text = format_rsi(50.0)
        assert text.justify == "right"


# -- format_macd --------------------------------------------------------------


class TestFormatMACD:
    """US-060: MACD formatted as 'symbol label' with bold colors."""

    def test_bull_content(self):
        text = format_macd("bull")
        assert text.plain == "\u25b2 bull"

    def test_bull_color_and_bold(self):
        text = format_macd("bull")
        style = _style_str(text)
        assert COLOR_POSITIVE.lstrip("#") in style
        assert "bold" in style

    def test_bear_content(self):
        text = format_macd("bear")
        assert text.plain == "\u25bc bear"

    def test_bear_color_and_bold(self):
        text = format_macd("bear")
        style = _style_str(text)
        assert COLOR_NEGATIVE.lstrip("#") in style
        assert "bold" in style

    def test_none_returns_na(self):
        text = format_macd(None)
        assert text.plain == "N/A"
        assert "dim" in _style_str(text)

    def test_right_justified(self):
        text = format_macd("bull")
        assert text.justify == "right"


# -- format_bb ----------------------------------------------------------------


class TestFormatBB:
    """US-060: Bollinger Band position (OB/OS/OK) with symbols."""

    def test_overbought_content(self):
        text = format_bb("overbought")
        assert text.plain == "\u25b2 OB"

    def test_overbought_color(self):
        text = format_bb("overbought")
        assert COLOR_OVERBOUGHT.lstrip("#") in _style_str(text)

    def test_oversold_content(self):
        text = format_bb("oversold")
        assert text.plain == "\u25bc OS"

    def test_oversold_color(self):
        text = format_bb("oversold")
        assert COLOR_OVERSOLD.lstrip("#") in _style_str(text)

    def test_neutral_content(self):
        text = format_bb("neutral")
        assert text.plain == "\u2014 OK"

    def test_neutral_color(self):
        text = format_bb("neutral")
        assert COLOR_NEUTRAL.lstrip("#") in _style_str(text)

    def test_none_returns_na(self):
        text = format_bb(None)
        assert text.plain == "N/A"
        assert "dim" in _style_str(text)

    def test_unknown_position_returns_na(self):
        text = format_bb("unknown_value")
        assert text.plain == "N/A"

    def test_right_justified(self):
        text = format_bb("neutral")
        assert text.justify == "right"


# -- format_confidence ---------------------------------------------------------


class TestFormatConfidence:
    """US-060: Confidence % with brightness gradient."""

    def test_high_value_content(self):
        text = format_confidence(0.85)
        assert text.plain == "85%"

    def test_high_value_bold_green(self):
        text = format_confidence(0.85)
        style = _style_str(text)
        assert COLOR_POSITIVE.lstrip("#") in style
        assert "bold" in style

    def test_medium_value_content(self):
        text = format_confidence(0.55)
        assert text.plain == "55%"

    def test_medium_value_neutral_color(self):
        text = format_confidence(0.55)
        assert COLOR_NEUTRAL.lstrip("#") in _style_str(text)

    def test_low_value_content(self):
        text = format_confidence(0.15)
        assert text.plain == "15%"

    def test_low_value_muted(self):
        text = format_confidence(0.15)
        assert "dim" in _style_str(text)

    def test_none_returns_na(self):
        text = format_confidence(None)
        assert text.plain == "N/A"
        assert "dim" in _style_str(text)

    def test_boundary_at_70(self):
        """0.7 is high confidence."""
        text = format_confidence(0.70)
        assert "bold" in _style_str(text)

    def test_boundary_at_40(self):
        """0.4 is medium confidence."""
        text = format_confidence(0.40)
        assert COLOR_NEUTRAL.lstrip("#") in _style_str(text)

    def test_boundary_below_40(self):
        """0.39 is low confidence."""
        text = format_confidence(0.39)
        assert "dim" in _style_str(text)

    def test_right_justified(self):
        text = format_confidence(0.5)
        assert text.justify == "right"


class TestInterpretationColors:
    def test_covers_all_interpretations(self):
        expected = {"bullish", "bearish", "neutral", "overbought", "oversold"}
        assert set(INTERPRETATION_COLORS.keys()) == expected

    def test_bullish_is_positive(self):
        assert INTERPRETATION_COLORS["bullish"] == COLOR_POSITIVE

    def test_bearish_is_negative(self):
        assert INTERPRETATION_COLORS["bearish"] == COLOR_NEGATIVE

    def test_overbought_matches(self):
        assert INTERPRETATION_COLORS["overbought"] == COLOR_OVERBOUGHT

    def test_oversold_matches(self):
        assert INTERPRETATION_COLORS["oversold"] == COLOR_OVERSOLD


class TestInterpretationSymbols:
    def test_covers_all_interpretations(self):
        expected = {"bullish", "bearish", "neutral", "overbought", "oversold"}
        assert set(INTERPRETATION_SYMBOLS.keys()) == expected

    def test_bullish_is_up_arrow(self):
        assert INTERPRETATION_SYMBOLS["bullish"] == "\u25b2"

    def test_bearish_is_down_arrow(self):
        assert INTERPRETATION_SYMBOLS["bearish"] == "\u25bc"

    def test_neutral_is_dash(self):
        assert INTERPRETATION_SYMBOLS["neutral"] == "\u2014"


class TestFormatInterpretation:
    def test_bullish(self):
        color, label = format_interpretation("bullish")
        assert color == COLOR_POSITIVE
        assert label == "Bullish"

    def test_bearish(self):
        color, label = format_interpretation("bearish")
        assert color == COLOR_NEGATIVE
        assert label == "Bearish"

    def test_none_returns_muted(self):
        color, label = format_interpretation(None)
        assert color == COLOR_MUTED
        assert label == ""

    def test_unknown_returns_muted(self):
        color, label = format_interpretation("unknown")
        assert color == COLOR_MUTED
        assert label == "Unknown"


class TestFormatTrend:
    def test_price_above_indicator(self):
        text = format_trend(170.0, 175.0)
        assert "170.00" in str(text)
        assert "\u25b2" in str(text)

    def test_price_below_indicator(self):
        text = format_trend(180.0, 175.0)
        assert "180.00" in str(text)
        assert "\u25bc" in str(text)

    def test_none_value(self):
        text = format_trend(None, 175.0)
        assert "N/A" in str(text)

    def test_none_close(self):
        text = format_trend(170.0, None)
        assert "N/A" in str(text)

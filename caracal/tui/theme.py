"""TUI color constants and formatting for semantic styling."""

from rich.text import Text
from textual.theme import Theme

# -- Caracal Dark theme (Textual Theme object) --------------------------------

CARACAL_THEME = Theme(
    name="caracal",
    primary="#56b6c2",      # Desaturated cyan (One Dark-inspired)
    secondary="#3d8b94",    # Muted teal
    accent="#c678dd",       # Purple/mauve contrast accent
    foreground="#abb2bf",   # Warm grey
    background="#1e2127",   # Dark background
    surface="#282c34",      # Widget backgrounds
    panel="#2c313a",        # Panel/container
    warning="#e5c07b",      # Muted gold
    error="#e06c75",        # Soft red
    success="#98c379",      # Soft green
    dark=True,
)

# Semantic colors — shared across all screens
COLOR_PRICE = "#56b6c2"
COLOR_POSITIVE = "#98c379"
COLOR_NEGATIVE = "#e06c75"
COLOR_MUTED = "dim"
COLOR_WARNING = "#e5c07b"
COLOR_OVERBOUGHT = "#e06c75"
COLOR_OVERSOLD = "#98c379"
COLOR_NEUTRAL = "#e5c07b"

SIGNAL_COLORS = {
    "buy": COLOR_POSITIVE,
    "sell": COLOR_NEGATIVE,
    "hold": COLOR_NEUTRAL,
}

INDICATOR_STYLES = {
    "overbought": COLOR_OVERBOUGHT,
    "oversold": COLOR_OVERSOLD,
    "neutral": COLOR_NEUTRAL,
}

INTERPRETATION_COLORS: dict[str, str] = {
    "bullish": COLOR_POSITIVE,
    "bearish": COLOR_NEGATIVE,
    "neutral": COLOR_NEUTRAL,
    "overbought": COLOR_OVERBOUGHT,
    "oversold": COLOR_OVERSOLD,
}

INTERPRETATION_SYMBOLS: dict[str, str] = {
    "bullish": "\u25b2",
    "bearish": "\u25bc",
    "neutral": "\u2014",
    "overbought": "\u25b2",
    "oversold": "\u25bc",
}


def format_interpretation(interpretation: str | None) -> tuple[str, str]:
    """Return (color, label) for an interpretation.

    Used by AssetDetailView for inline interpretation rendering.
    """
    if interpretation is None:
        return COLOR_MUTED, ""
    color = INTERPRETATION_COLORS.get(interpretation, COLOR_MUTED)
    label = interpretation.capitalize()
    return color, label


def format_trend(value: float | None, close: float | None) -> Text:
    """Format trend indicator (SMA/EMA) with price comparison."""
    if value is None or close is None:
        return Text("N/A", style=COLOR_MUTED, justify="right")
    color = COLOR_POSITIVE if close > value else COLOR_NEGATIVE
    symbol = "\u25b2" if close > value else "\u25bc"
    return Text(f"{value:.2f} {symbol}", style=color, justify="right")


def format_rsi(value: float | None) -> Text:
    """Format RSI as interpreted signal: 72▲ / 28▼ / 50—."""
    if value is None:
        return Text("N/A", style=COLOR_MUTED, justify="right")
    rounded = round(value)
    if value > 70:
        return Text(f"{rounded}\u25b2", style=COLOR_OVERBOUGHT, justify="right")
    if value < 30:
        return Text(f"{rounded}\u25bc", style=COLOR_OVERSOLD, justify="right")
    return Text(f"{rounded}\u2014", style=COLOR_NEUTRAL, justify="right")


def format_macd(interpretation: str | None) -> Text:
    """Format MACD as BULL/BEAR signal."""
    if interpretation is None:
        return Text("N/A", style=COLOR_MUTED, justify="right")
    if interpretation == "bull":
        return Text("BULL", style=f"bold {COLOR_POSITIVE}", justify="right")
    return Text("BEAR", style=f"bold {COLOR_NEGATIVE}", justify="right")


def format_bb(position: str | None) -> Text:
    """Format Bollinger Band position: ▲OB / ▼OS / —OK."""
    if position is None:
        return Text("N/A", style=COLOR_MUTED, justify="right")
    styles = {
        "overbought": ("\u25b2OB", COLOR_OVERBOUGHT),
        "oversold": ("\u25bcOS", COLOR_OVERSOLD),
        "neutral": ("\u2014OK", COLOR_NEUTRAL),
    }
    label, color = styles.get(position, ("N/A", COLOR_MUTED))
    return Text(label, style=color, justify="right")


def format_confidence(value: float | None) -> Text:
    """Format confidence as percentage with brightness gradient."""
    if value is None:
        return Text("N/A", style=COLOR_MUTED, justify="right")
    pct = round(value * 100)
    if value >= 0.7:
        style = f"bold {COLOR_POSITIVE}"
    elif value >= 0.4:
        style = COLOR_NEUTRAL
    else:
        style = COLOR_MUTED
    return Text(f"{pct}%", style=style, justify="right")

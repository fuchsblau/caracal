"""TUI color constants and formatting for semantic styling."""

from rich.text import Text

# Semantic colors — shared across all screens
COLOR_PRICE = "cyan"
COLOR_POSITIVE = "#4caf50"
COLOR_NEGATIVE = "#f44336"
COLOR_MUTED = "dim"
COLOR_WARNING = "#ff9800"
COLOR_OVERBOUGHT = "#f44336"
COLOR_OVERSOLD = "#4caf50"
COLOR_NEUTRAL = "#ffc107"

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

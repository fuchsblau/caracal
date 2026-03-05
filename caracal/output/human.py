"""Rich-based human-readable output formatter."""

from typing import Any

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.text import Text

from caracal.output.precision import PRICE_DECIMALS, VOLUME_DECIMALS

_PRICE_COLUMNS = {"open", "high", "low", "close"}

LOGO = (
    "░█▀▀░█▀█░█▀▄░█▀█░█▀▀░█▀█░█░░\n"
    "░█░░░█▀█░█▀▄░█▀█░█░░░█▀█░█░░\n"
    "░▀▀▀░▀░▀░▀░▀░▀░▀░▀▀▀░▀░▀░▀▀▀"
)


def format_logo() -> str:
    """Format the ASCII logo with styling."""
    console = Console(file=None, force_terminal=True)
    with console.capture() as capture:
        console.print(f"\n[bold]{LOGO}[/bold]\n")
    return capture.get()


def _format_ohlcv_cell(col: str, val: object) -> str:
    """Format a single OHLCV cell based on column name."""
    col_lower = str(col).lower()
    if col_lower in _PRICE_COLUMNS:
        return f"{val:.{PRICE_DECIMALS}f}"
    if col_lower == "volume":
        return f"{val:.{VOLUME_DECIMALS}f}"
    return str(val)


def format_ohlcv_table(df: pd.DataFrame, ticker: str) -> str:
    console = Console(file=None, force_terminal=True)
    table = Table(title=f"OHLCV – {ticker}")
    for col in df.columns:
        table.add_column(str(col).capitalize())
    for _, row in df.iterrows():
        table.add_row(*[_format_ohlcv_cell(col, v) for col, v in row.items()])
    with console.capture() as capture:
        console.print(table)
    return capture.get()


def format_error_message(message: str) -> str:
    console = Console(file=None, force_terminal=True)
    with console.capture() as capture:
        console.print(f"[bold red]Error:[/bold red] {message}")
    return capture.get()


def format_indicators_dict(indicators: dict[str, Any], ticker: str) -> str:
    """Format indicator results as a Rich table with color-coded values."""
    console = Console(file=None, force_terminal=True)
    table = Table(title=f"Indicators – {ticker}")
    table.add_column("Indicator", style="bold")
    table.add_column("Value", justify="right")

    for name, val in indicators.items():
        if val is None:
            table.add_row(name, Text("N/A", style="dim"))
        else:
            styled = _color_value(name, val)
            table.add_row(name, styled)

    with console.capture() as capture:
        console.print(table)
    return capture.get()


def format_entry_signal(result: dict[str, Any], ticker: str) -> str:
    """Format entry signal with color-coded signal and confidence."""
    console = Console(file=None, force_terminal=True)

    signal = result["signal"].upper()
    confidence = result["confidence"]

    signal_colors = {"BUY": "bold green", "SELL": "bold red", "HOLD": "bold yellow"}
    style = signal_colors.get(signal, "bold")

    with console.capture() as capture:
        console.print(
            f"\n[bold]{ticker}[/bold]: [{style}]{signal}[/{style}]"
            f" (confidence: {confidence:.0%})"
        )

        indicators = result.get("indicators", {})
        if indicators:
            table = Table(title="Indicators")
            table.add_column("Indicator", style="bold")
            table.add_column("Value", justify="right")
            for name, val in indicators.items():
                if val is None:
                    table.add_row(name, Text("N/A", style="dim"))
                else:
                    styled = _color_value(name, val)
                    table.add_row(name, styled)
            console.print(table)

    return capture.get()


def format_fetch_success(rows_added: int, ticker: str) -> str:
    """Format fetch success message."""
    console = Console(file=None, force_terminal=True)
    with console.capture() as capture:
        if rows_added == 0:
            console.print(f"[bold]{ticker}[/bold]: Already up to date.")
        else:
            console.print(
                f"[bold green]Fetched {rows_added} rows[/bold green]"
                f" for [bold]{ticker}[/bold]."
            )
    return capture.get()


def format_success_message(message: str, details: dict[str, str] | None = None) -> str:
    """Format a success message with optional key-value details."""
    console = Console(file=None, force_terminal=True)
    with console.capture() as capture:
        console.print(f"[bold green]{message}[/bold green]")
        if details:
            for key, val in details.items():
                console.print(f"  [bold]{key}:[/bold] {val}")
    return capture.get()


def format_warning(message: str) -> str:
    """Format a warning message."""
    console = Console(file=None, force_terminal=True)
    with console.capture() as capture:
        console.print(f"[bold yellow]Warning:[/bold yellow] {message}")
    return capture.get()


def format_header(title: str) -> str:
    """Format a section header."""
    console = Console(file=None, force_terminal=True)
    with console.capture() as capture:
        console.print(f"\n[bold]{title}[/bold]")
    return capture.get()


def format_watchlist_list(watchlists: list[dict]) -> str:
    """Format a list of watchlists as a Rich table."""
    console = Console(file=None, force_terminal=True)
    table = Table(title="Watchlists")
    table.add_column("Name", style="bold")
    table.add_column("Tickers", justify="right")
    table.add_column("Created")
    for wl in watchlists:
        table.add_row(
            wl["name"],
            str(wl["ticker_count"]),
            str(wl["created_at"]),
        )
    with console.capture() as capture:
        console.print(table)
    return capture.get()


def format_watchlist_items(tickers: list[str], watchlist_name: str) -> str:
    """Format watchlist ticker list as a Rich table."""
    console = Console(file=None, force_terminal=True)
    table = Table(title=f"Watchlist — {watchlist_name}")
    table.add_column("Ticker", style="bold")
    for ticker in tickers:
        table.add_row(ticker)
    with console.capture() as capture:
        console.print(table)
    return capture.get()


def format_watchlist_prices(prices: list[dict], watchlist_name: str) -> str:
    """Format watchlist prices as a Rich table with color-coded changes."""
    console = Console(file=None, force_terminal=True)
    table = Table(title=f"Watchlist — {watchlist_name}")
    table.add_column("Ticker", style="bold")
    table.add_column("Close", justify="right")
    table.add_column("Change", justify="right")
    table.add_column("Change%", justify="right")
    for p in prices:
        change = p.get("change")
        change_pct = p.get("change_pct")
        close_str = f"{p['close']:.2f}" if p.get("close") is not None else "N/A"
        if change is not None:
            style = "green" if change >= 0 else "red"
            change_str = Text(f"{change:+.2f}", style=style)
            pct_str = Text(f"{change_pct:+.2f}%", style=style)
        else:
            change_str = Text("N/A", style="dim")
            pct_str = Text("N/A", style="dim")
        table.add_row(p["ticker"], close_str, change_str, pct_str)
    with console.capture() as capture:
        console.print(table)
    return capture.get()


def _color_value(name: str, val: float) -> Text:
    """Apply color based on indicator semantics."""
    formatted = f"{val:.4f}"

    if "rsi" in name:
        if val > 70:
            return Text(formatted, style="red")
        elif val < 30:
            return Text(formatted, style="green")
        return Text(formatted)

    if val > 0:
        return Text(formatted, style="green")
    elif val < 0:
        return Text(formatted, style="red")
    return Text(formatted)

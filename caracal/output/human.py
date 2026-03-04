"""Rich-based human-readable output formatter."""

import pandas as pd
from rich.console import Console
from rich.table import Table


def format_ohlcv_table(df: pd.DataFrame, ticker: str) -> str:
    console = Console(file=None, force_terminal=False)
    table = Table(title=f"OHLCV – {ticker}")
    for col in df.columns:
        table.add_column(str(col).capitalize())
    for _, row in df.iterrows():
        table.add_row(*[str(v) for v in row])
    with console.capture() as capture:
        console.print(table)
    return capture.get()


def format_error_message(message: str) -> str:
    console = Console(file=None, force_terminal=False)
    with console.capture() as capture:
        console.print(f"[bold red]Error:[/bold red] {message}")
    return capture.get()


def format_indicators_table(df: pd.DataFrame, ticker: str) -> str:
    console = Console(file=None, force_terminal=False)
    table = Table(title=f"Indicators – {ticker}")
    for col in df.columns:
        table.add_column(str(col).capitalize())
    for _, row in df.iterrows():
        table.add_row(*[str(v) for v in row])
    with console.capture() as capture:
        console.print(table)
    return capture.get()

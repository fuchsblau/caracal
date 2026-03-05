"""Stock detail screen — indicators, OHLCV, signal."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

if TYPE_CHECKING:
    from caracal.tui.data import DataService

COLOR_PRICE = "cyan"
COLOR_MUTED = "dim"

SIGNAL_STYLES = {
    "buy": "[bold #4caf50]BUY[/]",
    "sell": "[bold #f44336]SELL[/]",
    "hold": "[bold #ffc107]HOLD[/]",
}


class StockDetailScreen(Screen):
    """Detail view for a single stock with indicators and OHLCV."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, ticker: str, data_service: DataService) -> None:
        super().__init__()
        self.ticker = ticker
        self.data_service = data_service

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield Static(id="detail-header")
            yield Static("[bold]Indicators[/]", classes="section-title")
            yield DataTable(id="indicators-table")
            yield Static("[bold]Recent OHLCV[/]", classes="section-title")
            yield DataTable(id="ohlcv-table")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self.ticker
        detail = self.data_service.get_stock_detail(self.ticker)

        # Header
        signal_display = SIGNAL_STYLES.get(detail["signal"], detail["signal"])
        close_str = f"{detail['close']:.2f}" if detail["close"] is not None else "N/A"
        pct_str = ""
        if detail["change_pct"] is not None:
            pct_str = f" ({detail['change_pct']:+.2f}%)"
        header_text = f"[bold]{self.ticker}[/]  {close_str}{pct_str}  {signal_display}"
        if detail["confidence"]:
            header_text += f"  Confidence: {detail['confidence']:.2%}"
        self.query_one("#detail-header", Static).update(header_text)

        # Indicators table
        ind_table = self.query_one("#indicators-table", DataTable)
        ind_table.add_columns("Indicator", "Value")
        for name, val in detail["indicators"].items():
            name_text = Text(name)
            if val is not None:
                val_text = Text(f"{val:.2f}", style=COLOR_PRICE, justify="right")
            else:
                val_text = Text("N/A", style=COLOR_MUTED, justify="right")
            ind_table.add_row(name_text, val_text)

        if not detail["indicators"]:
            ind_table.display = False

        # OHLCV table
        ohlcv_table = self.query_one("#ohlcv-table", DataTable)
        ohlcv_table.add_columns("Date", "Open", "High", "Low", "Close", "Volume")
        for row in detail["ohlcv"]:
            ohlcv_table.add_row(
                Text(row["date"]),
                Text(f"{row['open']:.2f}", style=COLOR_PRICE, justify="right"),
                Text(f"{row['high']:.2f}", style=COLOR_PRICE, justify="right"),
                Text(f"{row['low']:.2f}", style=COLOR_PRICE, justify="right"),
                Text(f"{row['close']:.2f}", style=COLOR_PRICE, justify="right"),
                Text(f"{row['volume']:,}", justify="right"),
            )

        if not detail["ohlcv"]:
            ohlcv_table.display = False
            msg = f"[bold]{self.ticker}[/]  No data."
            msg += f" Run 'caracal fetch {self.ticker}' first."
            self.query_one("#detail-header", Static).update(msg)

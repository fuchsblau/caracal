"""AssetDetailView -- detail widget for a single asset."""

from __future__ import annotations

from rich.text import Text
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import DataTable, Static

from caracal.tui.theme import (
    COLOR_MUTED,
    COLOR_PRICE,
    SIGNAL_COLORS,
)


class AssetDetailView(Widget):
    """Detail view showing all indicators and OHLCV for one asset."""

    def compose(self):
        with VerticalScroll():
            yield Static(id="detail-header")
            yield Static("[bold]Indicators[/]", classes="section-title")
            yield DataTable(id="indicators-table")
            yield Static("[bold]Recent OHLCV[/]", classes="section-title")
            yield DataTable(id="ohlcv-table")

    def on_mount(self) -> None:
        ind_table = self.query_one("#indicators-table", DataTable)
        ind_table.add_columns("Indicator", "Value")
        ohlcv_table = self.query_one("#ohlcv-table", DataTable)
        ohlcv_table.add_columns("Date", "Open", "High", "Low", "Close", "Volume")

    def load_detail(self, detail: dict) -> None:
        """Load asset detail data into the view."""
        # Header
        signal = detail["signal"]
        sig_color = SIGNAL_COLORS.get(signal, COLOR_MUTED)
        close_str = f"{detail['close']:.2f}" if detail["close"] is not None else "N/A"
        pct_str = ""
        if detail["change_pct"] is not None:
            pct_str = f" ({detail['change_pct']:+.2f}%)"
        header = f"[bold]{detail['ticker']}[/]  {close_str}{pct_str}"
        header += f"  [{sig_color}][bold]{signal.upper()}[/][/{sig_color}]"
        if detail.get("confidence"):
            header += f"  Confidence: {detail['confidence']:.0%}"
        self.query_one("#detail-header", Static).update(header)

        # Indicators
        ind_table = self.query_one("#indicators-table", DataTable)
        ind_table.clear()
        for name, val in detail.get("indicators", {}).items():
            name_text = Text(name)
            if val is not None:
                val_text = Text(f"{val:.2f}", style=COLOR_PRICE, justify="right")
            else:
                val_text = Text("N/A", style=COLOR_MUTED, justify="right")
            ind_table.add_row(name_text, val_text)

        # OHLCV
        ohlcv_table = self.query_one("#ohlcv-table", DataTable)
        ohlcv_table.clear()
        for row in detail.get("ohlcv", []):
            ohlcv_table.add_row(
                Text(row["date"]),
                Text(f"{row['open']:.2f}", style=COLOR_PRICE, justify="right"),
                Text(f"{row['high']:.2f}", style=COLOR_PRICE, justify="right"),
                Text(f"{row['low']:.2f}", style=COLOR_PRICE, justify="right"),
                Text(f"{row['close']:.2f}", style=COLOR_PRICE, justify="right"),
                Text(f"{row['volume']:,}", justify="right"),
            )

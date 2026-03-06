"""AssetDetailView -- detail widget for a single asset."""

from __future__ import annotations

from rich.text import Text
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import DataTable, Static

from caracal.tui.theme import (
    COLOR_MUTED,
    COLOR_NEGATIVE,
    COLOR_NEUTRAL,
    COLOR_POSITIVE,
    COLOR_PRICE,
    INTERPRETATION_SYMBOLS,
    SIGNAL_COLORS,
    format_interpretation,
)


class AssetDetailView(Widget):
    """Detail view with grouped indicator sections and OHLCV table."""

    def compose(self):
        with VerticalScroll():
            yield Static(id="detail-header")
            yield Static(id="indicator-sections")
            yield Static(
                "[bold]Price History (5 days)[/]", classes="section-title"
            )
            yield DataTable(id="ohlcv-table")

    def on_mount(self) -> None:
        ohlcv_table = self.query_one("#ohlcv-table", DataTable)
        ohlcv_table.add_columns("Date", "Open", "High", "Low", "Close", "Volume")

    def load_detail(self, detail: dict) -> None:
        """Load asset detail data into the view."""
        self._update_header(detail)
        self._update_indicators(detail)
        self._update_ohlcv(detail)

    def _update_header(self, detail: dict) -> None:
        """Render header with signal, confidence, and vote counts."""
        signal = detail["signal"]
        sig_color = SIGNAL_COLORS.get(signal, COLOR_MUTED)
        close_str = (
            f"{detail['close']:.2f}" if detail["close"] is not None else "N/A"
        )
        pct_str = ""
        if detail["change_pct"] is not None:
            pct_str = f" ({detail['change_pct']:+.2f}%)"

        header = f"[bold]{detail['ticker']}[/]  {close_str}{pct_str}"
        header += f"  [{sig_color}][bold]{signal.upper()}[/][/{sig_color}]"
        if detail.get("confidence"):
            header += f"  Confidence: {detail['confidence']:.0%}"

        vote_counts = detail.get("vote_counts")
        if vote_counts:
            header += self._format_vote_line(vote_counts)

        self.query_one("#detail-header", Static).update(header)

    def _format_vote_line(self, vc: dict) -> str:
        """Format vote counts as compact header line."""
        total = vc["total"]
        buy = vc["buy"]
        hold = vc["hold"]
        sell = vc["sell"]
        return (
            f"  \u2502  {total} Rules: "
            f"[{COLOR_POSITIVE}]{buy}\u00d7 \u25b2[/{COLOR_POSITIVE}] "
            f"[{COLOR_NEUTRAL}]{hold}\u00d7 \u2014[/{COLOR_NEUTRAL}] "
            f"[{COLOR_NEGATIVE}]{sell}\u00d7 \u25bc[/{COLOR_NEGATIVE}]"
        )

    def _update_indicators(self, detail: dict) -> None:
        """Render grouped indicator sections as Rich text."""
        sections = []
        for group in detail.get("indicator_groups", []):
            category = group["category"]
            indicators = group["indicators"]
            # Skip sections where all values are None
            if not any(ind["value"] is not None for ind in indicators):
                continue
            section = f"\n[bold $primary]{category}[/]\n"
            section += "\u2500" * 44 + "\n"
            for ind in indicators:
                section += self._format_indicator_line(ind)
            sections.append(section)

        self.query_one("#indicator-sections", Static).update(
            "\n".join(sections) if sections else ""
        )

    def _format_indicator_line(self, ind: dict) -> str:
        """Format a single indicator with name, value, and interpretation."""
        name = ind["name"]
        value = ind["value"]
        interpretation = ind["interpretation"]
        detail_str = ind.get("detail") or ""

        if value is None:
            return f"  {name:<16} [dim]N/A[/]\n"

        val_str = f"{value:.2f}"
        color, _ = format_interpretation(interpretation)
        symbol = INTERPRETATION_SYMBOLS.get(interpretation, "")

        if symbol and detail_str:
            return (
                f"  {name:<16} [{COLOR_PRICE}]{val_str:>10}[/{COLOR_PRICE}]"
                f"   [{color}]{symbol} {detail_str}[/{color}]\n"
            )
        return f"  {name:<16} [{COLOR_PRICE}]{val_str:>10}[/{COLOR_PRICE}]\n"

    def _update_ohlcv(self, detail: dict) -> None:
        """Populate OHLCV table with price history."""
        ohlcv_table = self.query_one("#ohlcv-table", DataTable)
        ohlcv_table.clear()
        for row in detail.get("ohlcv", []):
            ohlcv_table.add_row(
                Text(row["date"]),
                Text(
                    f"{row['open']:.2f}", style=COLOR_PRICE, justify="right"
                ),
                Text(
                    f"{row['high']:.2f}", style=COLOR_PRICE, justify="right"
                ),
                Text(
                    f"{row['low']:.2f}", style=COLOR_PRICE, justify="right"
                ),
                Text(
                    f"{row['close']:.2f}", style=COLOR_PRICE, justify="right"
                ),
                Text(f"{row['volume']:,}", justify="right"),
            )

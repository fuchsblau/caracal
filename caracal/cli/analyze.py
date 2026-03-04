"""caracal analyze -- Calculate technical indicators."""

import click
import pandas as pd

from caracal.indicators.bollinger import BollingerIndicator
from caracal.indicators.ema import EMAIndicator
from caracal.indicators.macd import MACDIndicator
from caracal.indicators.rsi import RSIIndicator
from caracal.indicators.sma import SMAIndicator
from caracal.output import human as human_out
from caracal.output import json as json_out
from caracal.storage.duckdb import DuckDBStorage


def get_storage():
    return DuckDBStorage()


INDICATORS = [
    SMAIndicator(20),
    SMAIndicator(50),
    EMAIndicator(12),
    EMAIndicator(26),
    RSIIndicator(14),
    MACDIndicator(),
    BollingerIndicator(),
]


@click.command()
@click.argument("ticker")
@click.pass_context
def analyze(ctx: click.Context, ticker: str) -> None:
    """Calculate technical indicators for TICKER."""
    output_format = ctx.obj["format"]
    meta = {"ticker": ticker, "command": "analyze"}
    storage = get_storage()

    try:
        df = storage.get_ohlcv(ticker)
        if df.empty:
            if output_format == "json":
                click.echo(
                    json_out.format_error(
                        "NO_DATA", f"No data found for {ticker}", meta
                    )
                )
            else:
                click.echo(
                    human_out.format_error_message(
                        f"No data for {ticker}. Run 'caracal fetch {ticker}' first."
                    )
                )
            ctx.exit(2)
            return

        results = {}
        for ind in INDICATORS:
            value = ind.calculate(df)
            if isinstance(value, pd.DataFrame):
                for col in value.columns:
                    results[f"{ind.name}_{col}"] = _to_json_safe(value[col].iloc[-1])
            else:
                results[ind.name] = _to_json_safe(value.iloc[-1])

        if output_format == "json":
            click.echo(json_out.format_success({"indicators": results}, meta))
        else:
            click.echo(f"Indicators for {ticker}:")
            for name, val in results.items():
                if val is not None:
                    click.echo(f"  {name}: {val:.4f}")
                else:
                    click.echo(f"  {name}: N/A")
    finally:
        storage.close()


def _to_json_safe(val):
    """Convert NaN to None for JSON serialization."""
    if pd.isna(val):
        return None
    return float(val)

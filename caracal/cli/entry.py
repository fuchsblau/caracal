"""caracal entry -- Calculate entry point recommendation."""

import click

from caracal.analysis.entry_points import calculate_entry_signal
from caracal.output import human as human_out
from caracal.output import json as json_out
from caracal.storage.duckdb import DuckDBStorage


def get_storage():
    return DuckDBStorage()


@click.command()
@click.argument("ticker")
@click.pass_context
def entry(ctx: click.Context, ticker: str) -> None:
    """Calculate entry point recommendation for TICKER."""
    output_format = ctx.obj["format"]
    meta = {"ticker": ticker, "command": "entry"}
    storage = get_storage()

    try:
        df = storage.get_ohlcv(ticker)
        if df.empty:
            if output_format == "json":
                click.echo(
                    json_out.format_error("NO_DATA", f"No data for {ticker}", meta)
                )
            else:
                click.echo(
                    human_out.format_error_message(
                        f"No data for {ticker}. Run 'caracal fetch {ticker}' first."
                    )
                )
            ctx.exit(2)
            return

        result = calculate_entry_signal(df)

        if output_format == "json":
            click.echo(json_out.format_success(result, meta))
        else:
            signal = result["signal"].upper()
            confidence = result["confidence"]
            click.echo(f"{ticker}: {signal} (confidence: {confidence:.0%})")
            if result.get("indicators"):
                for name, val in result["indicators"].items():
                    if val is not None:
                        click.echo(f"  {name}: {val:.4f}")
    finally:
        storage.close()

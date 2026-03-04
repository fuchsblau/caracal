"""caracal entry -- Calculate entry point recommendation."""

import click

from caracal.analysis.entry_points import calculate_entry_signal
from caracal.output import human as human_out
from caracal.output import json as json_out
from caracal.storage.duckdb import DuckDBStorage


def get_storage(db_path: str = "~/.caracal/caracal.db"):
    return DuckDBStorage(db_path)


@click.command()
@click.argument("ticker")
@click.pass_context
def entry(ctx: click.Context, ticker: str) -> None:
    """Calculate entry point recommendation for TICKER."""
    output_format = ctx.obj["format"]
    meta = {"ticker": ticker, "command": "entry"}
    config = ctx.obj["config"]
    storage = get_storage(config.db_path)

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
            click.echo(human_out.format_entry_signal(result, ticker))
    finally:
        storage.close()

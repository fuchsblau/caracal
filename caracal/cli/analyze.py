"""caracal analyze -- Calculate technical indicators."""

import click
import pandas as pd

from caracal.analysis.compute import compute_indicators as _compute_indicators
from caracal.output import human as human_out
from caracal.output import json as json_out
from caracal.storage.duckdb import DuckDBStorage


def get_storage(db_path: str = "~/.caracal/caracal.db"):
    return DuckDBStorage(db_path)


@click.command()
@click.argument("ticker")
@click.pass_context
def analyze(ctx: click.Context, ticker: str) -> None:
    """Calculate technical indicators for TICKER."""
    output_format = ctx.obj["format"]
    meta = {"ticker": ticker, "command": "analyze"}
    config = ctx.obj["config"]
    storage = get_storage(config.db_path)

    try:
        df = storage.get_ohlcv(ticker)
        if df.empty:
            _output_no_data(output_format, ticker, meta)
            ctx.exit(2)
            return

        results, indicator_rows = _compute_indicators(df)

        if indicator_rows:
            ind_df = pd.DataFrame(indicator_rows)
            storage.store_indicators(ticker, ind_df)

        if output_format == "json":
            click.echo(json_out.format_success({"indicators": results}, meta))
        else:
            click.echo(human_out.format_indicators_dict(results, ticker))
    finally:
        storage.close()


def _output_no_data(fmt: str, ticker: str, meta: dict) -> None:
    if fmt == "json":
        click.echo(
            json_out.format_error("NO_DATA", f"No data found for {ticker}", meta)
        )
    else:
        click.echo(
            human_out.format_error_message(
                f"No data for {ticker}. Run 'caracal fetch {ticker}' first."
            )
        )



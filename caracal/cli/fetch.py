"""caracal fetch -- Fetch market data."""

from datetime import date, timedelta

import click

from caracal.output import human as human_out
from caracal.output import json as json_out
from caracal.providers import get_provider as _get_provider
from caracal.providers.types import ProviderError, StorageError, TickerNotFoundError
from caracal.storage.duckdb import DuckDBStorage


def get_provider(name: str = "yahoo"):
    return _get_provider(name)


def get_storage():
    return DuckDBStorage()


@click.command()
@click.argument("ticker")
@click.option("--period", default="1y", help="Period to fetch (e.g. 1y, 6mo, 3mo).")
@click.option("--provider", default="yahoo", help="Data provider to use.")
@click.pass_context
def fetch(ctx: click.Context, ticker: str, period: str, provider: str) -> None:
    """Fetch OHLCV data for TICKER."""
    output_format = ctx.obj["format"]
    meta = {"ticker": ticker, "command": "fetch"}

    try:
        prov = get_provider(provider)
    except ValueError as e:
        _output_error(output_format, "UNKNOWN_PROVIDER", str(e), meta)
        ctx.exit(1)
        return

    storage = get_storage()

    end_date = date.today()
    start_date = _parse_period(period, end_date)

    try:
        # Delta-fetch: check latest date in storage
        latest = storage.get_latest_date(ticker)
        if latest:
            start_date = latest + timedelta(days=1)
            if start_date > end_date:
                _output_success(
                    output_format,
                    {
                        "rows_added": 0,
                        "ticker": ticker,
                        "message": "Already up to date",
                    },
                    meta,
                )
                return

        df = prov.fetch_ohlcv(ticker, start_date, end_date)
        count = storage.store_ohlcv(ticker, df)
        _output_success(output_format, {"rows_added": count, "ticker": ticker}, meta)
    except TickerNotFoundError as e:
        _output_error(output_format, "INVALID_TICKER", str(e), meta)
        ctx.exit(2)
    except ProviderError as e:
        _output_error(output_format, "PROVIDER_ERROR", str(e), meta)
        ctx.exit(1)
    except StorageError as e:
        _output_error(output_format, "STORAGE_ERROR", str(e), meta)
        ctx.exit(1)
    finally:
        storage.close()


def _parse_period(period: str, end_date: date) -> date:
    mapping = {"1y": 365, "6mo": 182, "3mo": 91, "1mo": 30, "5y": 1825}
    days = mapping.get(period, 365)
    return end_date - timedelta(days=days)


def _output_success(fmt: str, data: dict, meta: dict) -> None:
    if fmt == "json":
        click.echo(json_out.format_success(data, meta))
    else:
        click.echo(
            f"Fetched {data.get('rows_added', 0)} rows for {data.get('ticker', '?')}"
        )


def _output_error(fmt: str, code: str, message: str, meta: dict) -> None:
    if fmt == "json":
        click.echo(json_out.format_error(code, message, meta))
    else:
        click.echo(human_out.format_error_message(message))

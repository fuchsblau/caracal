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


def get_storage(db_path: str = "~/.caracal/caracal.db"):
    return DuckDBStorage(db_path)


@click.command()
@click.argument("ticker")
@click.option("--period", default=None, help="Period to fetch (e.g. 1y, 6mo, 3mo).")
@click.option("--provider", default=None, help="Data provider to use.")
@click.pass_context
def fetch(
    ctx: click.Context,
    ticker: str,
    period: str | None,
    provider: str | None,
) -> None:
    """Fetch OHLCV data for TICKER."""
    config = ctx.obj["config"]
    output_format = ctx.obj["format"]
    meta = {"ticker": ticker, "command": "fetch"}

    effective_period = period or config.default_period
    effective_provider = provider or config.default_provider

    try:
        prov = get_provider(effective_provider)
    except ValueError as e:
        _output_error(output_format, "UNKNOWN_PROVIDER", str(e), meta)
        ctx.exit(1)
        return

    storage = get_storage(config.db_path)

    end_date = date.today()
    start_date = _parse_period(effective_period, end_date)

    try:
        # Delta-fetch: check latest date in storage
        latest = storage.get_latest_date(ticker)
        if latest:
            start_date = latest + timedelta(days=1)
            if start_date > end_date:
                if output_format == "json":
                    click.echo(
                        json_out.format_success(
                            {
                                "rows_added": 0,
                                "ticker": ticker,
                                "message": "Already up to date",
                            },
                            meta,
                        )
                    )
                else:
                    click.echo(human_out.format_fetch_success(0, ticker))
                return

        df = prov.fetch_ohlcv(ticker, start_date, end_date)
        count = storage.store_ohlcv(ticker, df)
        if output_format == "json":
            click.echo(
                json_out.format_success({"rows_added": count, "ticker": ticker}, meta)
            )
        else:
            click.echo(human_out.format_fetch_success(count, ticker))
            if not df.empty:
                click.echo(human_out.format_ohlcv_table(df.tail(10), ticker))
    except TickerNotFoundError:
        if latest:
            # Delta-fetch: we have data, just nothing new
            if output_format == "json":
                click.echo(
                    json_out.format_success(
                        {
                            "rows_added": 0,
                            "ticker": ticker,
                            "message": "No new data available",
                        },
                        meta,
                    )
                )
            else:
                click.echo(human_out.format_fetch_success(0, ticker))
        else:
            _output_error(
                output_format,
                "INVALID_TICKER",
                f"Ticker not found: {ticker}",
                meta,
            )
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


def _output_error(fmt: str, code: str, message: str, meta: dict) -> None:
    if fmt == "json":
        click.echo(json_out.format_error(code, message, meta))
    else:
        click.echo(human_out.format_error_message(message))

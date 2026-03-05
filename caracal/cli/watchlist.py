"""caracal watchlist -- Manage watchlists."""

from datetime import date, timedelta

import click

from caracal.config import CaracalConfig
from caracal.output import human as human_out
from caracal.output import json as json_out
from caracal.providers import get_provider as _get_provider
from caracal.providers.types import ProviderError, StorageError
from caracal.storage.duckdb import DuckDBStorage


def get_provider(name: str = "yahoo", config: CaracalConfig | None = None):
    kwargs = {}
    if config and name in config.providers:
        kwargs = config.providers[name]
    return _get_provider(name, **kwargs)


def get_storage(db_path: str = "~/.caracal/caracal.db"):
    return DuckDBStorage(db_path)


@click.group()
@click.pass_context
def watchlist(ctx: click.Context) -> None:
    """Manage watchlists."""


@watchlist.command()
@click.argument("name")
@click.pass_context
def create(ctx: click.Context, name: str) -> None:
    """Create a new watchlist."""
    config = ctx.obj["config"]
    output_format = ctx.obj["format"]
    meta = {"command": "watchlist create", "watchlist": name}

    storage = get_storage(config.db_path)
    try:
        storage.create_watchlist(name)
        if output_format == "json":
            click.echo(json_out.format_success({"watchlist": name}, meta))
        else:
            click.echo(human_out.format_success_message(f"Watchlist '{name}' created."))
    except StorageError as e:
        _output_error(output_format, "STORAGE_ERROR", str(e), meta)
        ctx.exit(1)
    finally:
        storage.close()


@watchlist.command()
@click.argument("name")
@click.pass_context
def delete(ctx: click.Context, name: str) -> None:
    """Delete a watchlist."""
    config = ctx.obj["config"]
    output_format = ctx.obj["format"]
    meta = {"command": "watchlist delete", "watchlist": name}

    storage = get_storage(config.db_path)
    try:
        storage.delete_watchlist(name)
        if output_format == "json":
            click.echo(json_out.format_success({"watchlist": name}, meta))
        else:
            click.echo(human_out.format_success_message(f"Watchlist '{name}' deleted."))
    except StorageError as e:
        _output_error(output_format, "STORAGE_ERROR", str(e), meta)
        ctx.exit(1)
    finally:
        storage.close()


@watchlist.command("add")
@click.argument("name")
@click.argument("tickers", nargs=-1, required=True)
@click.pass_context
def add_tickers(ctx: click.Context, name: str, tickers: tuple[str, ...]) -> None:
    """Add tickers to a watchlist."""
    config = ctx.obj["config"]
    output_format = ctx.obj["format"]
    meta = {"command": "watchlist add", "watchlist": name}

    storage = get_storage(config.db_path)
    try:
        added = []
        for ticker in tickers:
            storage.add_to_watchlist(name, ticker.upper())
            added.append(ticker.upper())
        if output_format == "json":
            click.echo(
                json_out.format_success({"watchlist": name, "added": added}, meta)
            )
        else:
            tickers_str = ", ".join(added)
            click.echo(
                human_out.format_success_message(f"Added {tickers_str} to '{name}'.")
            )
    except StorageError as e:
        _output_error(output_format, "STORAGE_ERROR", str(e), meta)
        ctx.exit(1)
    finally:
        storage.close()


@watchlist.command("remove")
@click.argument("name")
@click.argument("ticker")
@click.pass_context
def remove_ticker(ctx: click.Context, name: str, ticker: str) -> None:
    """Remove a ticker from a watchlist."""
    config = ctx.obj["config"]
    output_format = ctx.obj["format"]
    meta = {"command": "watchlist remove", "watchlist": name}

    storage = get_storage(config.db_path)
    try:
        storage.remove_from_watchlist(name, ticker.upper())
        if output_format == "json":
            click.echo(
                json_out.format_success(
                    {"watchlist": name, "removed": ticker.upper()}, meta
                )
            )
        else:
            click.echo(
                human_out.format_success_message(
                    f"Removed {ticker.upper()} from '{name}'."
                )
            )
    except StorageError as e:
        _output_error(output_format, "STORAGE_ERROR", str(e), meta)
        ctx.exit(1)
    finally:
        storage.close()


@watchlist.command("list")
@click.pass_context
def list_watchlists(ctx: click.Context) -> None:
    """List all watchlists."""
    config = ctx.obj["config"]
    output_format = ctx.obj["format"]
    meta = {"command": "watchlist list"}

    storage = get_storage(config.db_path)
    try:
        watchlists = storage.get_watchlists()
        if output_format == "json":
            click.echo(json_out.format_success({"watchlists": watchlists}, meta))
        else:
            if not watchlists:
                msg = (
                    "No watchlists found. Create one with:"
                    " caracal watchlist create <name>"
                )
                click.echo(human_out.format_warning(msg))
            else:
                click.echo(human_out.format_watchlist_list(watchlists))
    except StorageError as e:
        _output_error(output_format, "STORAGE_ERROR", str(e), meta)
        ctx.exit(1)
    finally:
        storage.close()


@watchlist.command("show")
@click.argument("name")
@click.pass_context
def show(ctx: click.Context, name: str) -> None:
    """Show current prices for all tickers in a watchlist."""
    config = ctx.obj["config"]
    output_format = ctx.obj["format"]
    meta = {"command": "watchlist show", "watchlist": name}

    storage = get_storage(config.db_path)
    try:
        tickers = storage.get_watchlist_items(name)
        if not tickers:
            if output_format == "json":
                data = {
                    "watchlist": name,
                    "prices": [],
                    "message": "No tickers in watchlist",
                }
                click.echo(json_out.format_success(data, meta))
            else:
                msg = (
                    f"Watchlist '{name}' is empty."
                    f" Add tickers with:"
                    f" caracal watchlist add {name} <ticker>"
                )
                click.echo(human_out.format_warning(msg))
            return

        try:
            provider = get_provider(config.default_provider, config)
        except ImportError as e:
            _output_error(output_format, "MISSING_DEPENDENCY", str(e), meta)
            ctx.exit(1)
            return

        end_date = date.today()
        start_date = end_date - timedelta(days=5)

        prices = []
        for ticker in tickers:
            try:
                df = provider.fetch_ohlcv(ticker, start_date, end_date)
                if len(df) >= 2:
                    close = float(df.iloc[-1]["close"])
                    prev_close = float(df.iloc[-2]["close"])
                    change = close - prev_close
                    change_pct = (change / prev_close) * 100
                    prices.append(
                        {
                            "ticker": ticker,
                            "close": close,
                            "change": change,
                            "change_pct": change_pct,
                        }
                    )
                elif len(df) == 1:
                    prices.append(
                        {
                            "ticker": ticker,
                            "close": float(df.iloc[-1]["close"]),
                            "change": None,
                            "change_pct": None,
                        }
                    )
                else:
                    prices.append(
                        {
                            "ticker": ticker,
                            "close": None,
                            "change": None,
                            "change_pct": None,
                        }
                    )
            except ProviderError:
                prices.append(
                    {
                        "ticker": ticker,
                        "close": None,
                        "change": None,
                        "change_pct": None,
                    }
                )

        if output_format == "json":
            click.echo(
                json_out.format_success({"watchlist": name, "prices": prices}, meta)
            )
        else:
            click.echo(human_out.format_watchlist_prices(prices, name))
    except StorageError as e:
        _output_error(output_format, "STORAGE_ERROR", str(e), meta)
        ctx.exit(1)
    finally:
        storage.close()


def _output_error(fmt: str, code: str, message: str, meta: dict) -> None:
    if fmt == "json":
        click.echo(json_out.format_error(code, message, meta))
    else:
        click.echo(human_out.format_error_message(message))

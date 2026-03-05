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


def get_storage(db_path: str = "~/.caracal/caracal.db"):
    return DuckDBStorage(db_path)


INDICATORS = [
    SMAIndicator(20),
    SMAIndicator(50),
    SMAIndicator(200),
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


def _compute_indicators(df: pd.DataFrame) -> tuple[dict, list[dict]]:
    results: dict = {}
    rows: list[dict] = []
    for ind in INDICATORS:
        value = ind.calculate(df)
        if isinstance(value, pd.DataFrame):
            _collect_dataframe_indicator(results, rows, df, ind.name, value)
        else:
            _collect_series_indicator(results, rows, df, ind.name, value)
    return results, rows


def _collect_dataframe_indicator(
    results: dict, rows: list[dict], df: pd.DataFrame, name: str, value: pd.DataFrame
) -> None:
    for col in value.columns:
        col_name = f"{name}_{col}"
        results[col_name] = _to_json_safe(value[col].iloc[-1])
        for dt, val in zip(df["date"], value[col]):
            rows.append({"date": dt, "name": col_name, "value": _to_json_safe(val)})


def _collect_series_indicator(
    results: dict, rows: list[dict], df: pd.DataFrame, name: str, value: pd.Series
) -> None:
    results[name] = _to_json_safe(value.iloc[-1])
    for dt, val in zip(df["date"], value):
        rows.append({"date": dt, "name": name, "value": _to_json_safe(val)})


def _to_json_safe(val):
    """Convert NaN to None for JSON serialization."""
    if pd.isna(val):
        return None
    return float(val)

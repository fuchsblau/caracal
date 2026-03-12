"""Shared indicator computation logic."""

import pandas as pd

from caracal.indicators.bollinger import BollingerIndicator
from caracal.indicators.ema import EMAIndicator
from caracal.indicators.macd import MACDIndicator
from caracal.indicators.rsi import RSIIndicator
from caracal.indicators.sma import SMAIndicator

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


def compute_indicators(df: pd.DataFrame) -> tuple[dict, list[dict]]:
    """Calculate all indicators for OHLCV data.

    Returns:
        (results_dict, storage_rows) where results_dict maps indicator
        names to latest values, and storage_rows is a list of dicts
        suitable for DataFrame construction and storage.
    """
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
    if pd.isna(val):
        return None
    return float(val)

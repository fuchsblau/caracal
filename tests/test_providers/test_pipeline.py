"""Tests for the normalization pipeline and NormalizedProvider decorator."""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock, PropertyMock

import pandas as pd
import pytest

from caracal.providers.types import (
    OHLCV_COLUMNS,
    TickerNotFoundError,
    assert_ohlcv_schema,
)


def _make_df(**overrides: object) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame with sensible defaults."""
    data = {
        "date": [date(2024, 1, 1), date(2024, 1, 2)],
        "open": [100.0, 101.0],
        "high": [105.0, 106.0],
        "low": [99.0, 100.0],
        "close": [104.0, 105.0],
        "volume": [1000, 1100],
    }
    data.update(overrides)
    return pd.DataFrame(data)


class TestNormalizePipeline:
    """Tests for the normalize_pipeline function."""

    def test_float_volume_cast_to_int(self) -> None:
        from caracal.providers.pipeline import normalize_pipeline

        df = _make_df(volume=[1000.7, 1100.3])
        result = normalize_pipeline(df)
        assert result["volume"].dtype == int
        assert list(result["volume"]) == [1000, 1100]

    def test_unsorted_dates_sorted_ascending(self) -> None:
        from caracal.providers.pipeline import normalize_pipeline

        df = _make_df(
            date=[date(2024, 1, 5), date(2024, 1, 2)],
            open=[200.0, 100.0],
        )
        result = normalize_pipeline(df)
        assert list(result["date"]) == [date(2024, 1, 2), date(2024, 1, 5)]
        assert list(result["open"]) == [100.0, 200.0]

    def test_datetime_converted_to_date(self) -> None:
        from caracal.providers.pipeline import normalize_pipeline

        df = _make_df(
            date=[datetime(2024, 1, 1, 9, 30), datetime(2024, 1, 2, 9, 30)],
        )
        result = normalize_pipeline(df)
        assert all(type(d) is date for d in result["date"])

    def test_extra_columns_stripped(self) -> None:
        from caracal.providers.pipeline import normalize_pipeline

        df = _make_df()
        df["adjusted_close"] = [103.0, 104.0]
        df["dividend"] = [0.5, 0.0]
        result = normalize_pipeline(df)
        assert list(result.columns) == OHLCV_COLUMNS

    def test_idempotent(self) -> None:
        from caracal.providers.pipeline import normalize_pipeline

        df = _make_df()
        first = normalize_pipeline(df.copy())
        second = normalize_pipeline(first.copy())
        pd.testing.assert_frame_equal(first, second)

    def test_index_reset(self) -> None:
        from caracal.providers.pipeline import normalize_pipeline

        df = _make_df(date=[date(2024, 1, 5), date(2024, 1, 2)])
        result = normalize_pipeline(df)
        assert list(result.index) == [0, 1]

    def test_ohlc_cast_to_float(self) -> None:
        from caracal.providers.pipeline import normalize_pipeline

        df = _make_df(open=[100, 101], high=[105, 106], low=[99, 100], close=[104, 105])
        result = normalize_pipeline(df)
        for col in ("open", "high", "low", "close"):
            assert result[col].dtype == float

    def test_empty_dataframe_passthrough(self) -> None:
        from caracal.providers.pipeline import normalize_pipeline

        df = pd.DataFrame(columns=OHLCV_COLUMNS)
        result = normalize_pipeline(df)
        assert result.empty
        assert list(result.columns) == OHLCV_COLUMNS

    def test_schema_valid_after_pipeline(self) -> None:
        from caracal.providers.pipeline import normalize_pipeline

        df = _make_df(
            date=[datetime(2024, 1, 3, 12, 0), datetime(2024, 1, 1, 9, 0)],
            open=[100, 101],
            volume=[500.9, 600.1],
        )
        df["extra"] = [1, 2]
        result = normalize_pipeline(df)
        assert_ohlcv_schema(result)


class TestNormalizedProvider:
    """Tests for the NormalizedProvider decorator."""

    def test_proxies_name(self) -> None:
        from caracal.providers.pipeline import NormalizedProvider

        inner = MagicMock()
        type(inner).name = PropertyMock(return_value="test_provider")
        provider = NormalizedProvider(inner)
        assert provider.name == "test_provider"

    def test_proxies_validate_ticker(self) -> None:
        from caracal.providers.pipeline import NormalizedProvider

        inner = MagicMock()
        inner.validate_ticker.return_value = True
        provider = NormalizedProvider(inner)
        assert provider.validate_ticker("AAPL") is True
        inner.validate_ticker.assert_called_once_with("AAPL")

    def test_normalizes_fetch_output(self) -> None:
        from caracal.providers.pipeline import NormalizedProvider

        raw = _make_df(
            date=[date(2024, 1, 5), date(2024, 1, 2)],
            open=[200, 100],
            volume=[500.5, 600.5],
        )
        raw["adjusted_close"] = [199.0, 99.0]
        inner = MagicMock()
        inner.fetch_ohlcv.return_value = raw

        provider = NormalizedProvider(inner)
        result = provider.fetch_ohlcv("AAPL", date(2024, 1, 1), date(2024, 1, 31))

        # Sorted ascending
        assert list(result["date"]) == [date(2024, 1, 2), date(2024, 1, 5)]
        # Volume cast to int
        assert result["volume"].dtype == int
        # OHLC cast to float
        assert result["open"].dtype == float
        # Extra columns stripped
        assert list(result.columns) == OHLCV_COLUMNS

    def test_passes_through_exceptions(self) -> None:
        from caracal.providers.pipeline import NormalizedProvider

        inner = MagicMock()
        inner.fetch_ohlcv.side_effect = TickerNotFoundError("INVALID")
        provider = NormalizedProvider(inner)

        with pytest.raises(TickerNotFoundError, match="INVALID"):
            provider.fetch_ohlcv("INVALID", date(2024, 1, 1), date(2024, 1, 31))

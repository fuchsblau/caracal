"""Tests for provider registry and lazy loading."""

from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

from caracal.providers.types import assert_ohlcv_schema


class TestProviderRegistry:
    def test_get_provider_returns_yahoo(self):
        from caracal.providers import get_provider

        provider = get_provider("yahoo")
        assert provider.name == "yahoo"

    def test_get_provider_unknown_raises_valueerror(self):
        from caracal.providers import get_provider

        with pytest.raises(ValueError, match="Unknown provider: nonexistent"):
            get_provider("nonexistent")

    def test_get_provider_unknown_lists_available(self):
        from caracal.providers import get_provider

        with pytest.raises(ValueError, match="yahoo"):
            get_provider("nonexistent")

    def test_get_provider_missing_dep_raises_importerror(self):
        from caracal.providers import get_provider

        # Patch on the importlib module attr — works because providers/__init__.py
        # uses `importlib.import_module()` (attribute access, not from-import).
        with patch("importlib.import_module", side_effect=ImportError("No module")):
            with pytest.raises(ImportError, match="pip install caracal"):
                get_provider("massive")

    def test_provider_map_contains_all_providers(self):
        from caracal.providers import _PROVIDER_MAP

        assert "yahoo" in _PROVIDER_MAP
        assert "massive" in _PROVIDER_MAP
        assert "ibkr" in _PROVIDER_MAP


class TestNormalizedProviderIntegration:
    def test_get_provider_returns_normalized(self):
        from caracal.providers import get_provider
        from caracal.providers.pipeline import NormalizedProvider

        provider = get_provider("yahoo")
        assert isinstance(provider, NormalizedProvider)

    def test_normalized_provider_preserves_name(self):
        from caracal.providers import get_provider

        provider = get_provider("yahoo")
        assert provider.name == "yahoo"

    def test_provider_map_contains_new_providers(self):
        from caracal.providers import _PROVIDER_MAP

        assert "alphavantage" in _PROVIDER_MAP
        assert "eodhd" in _PROVIDER_MAP
        assert "finnhub" in _PROVIDER_MAP


class TestOHLCVSchema:
    def test_valid_dataframe_passes(self):
        df = pd.DataFrame({
            "date": [date(2024, 1, 2), date(2024, 1, 3)],
            "open": [100.0, 101.0],
            "high": [105.0, 106.0],
            "low": [99.0, 100.0],
            "close": [104.0, 105.0],
            "volume": [1000000, 1100000],
        })
        assert_ohlcv_schema(df)  # Should not raise

    def test_missing_column_raises(self):
        df = pd.DataFrame({
            "date": [date(2024, 1, 2)],
            "open": [100.0],
            "high": [105.0],
        })
        with pytest.raises(AssertionError, match="Missing columns"):
            assert_ohlcv_schema(df)

    def test_unsorted_raises(self):
        df = pd.DataFrame({
            "date": [date(2024, 1, 3), date(2024, 1, 2)],
            "open": [101.0, 100.0],
            "high": [106.0, 105.0],
            "low": [100.0, 99.0],
            "close": [105.0, 104.0],
            "volume": [1100000, 1000000],
        })
        with pytest.raises(AssertionError, match="not sorted"):
            assert_ohlcv_schema(df)

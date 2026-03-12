"""Integration test: daemon run-once with real storage."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from caracal.config import CaracalConfig
from caracal.daemon.service import DaemonService


def _make_ohlcv(days: int = 250) -> pd.DataFrame:
    start = date(2025, 1, 1)
    dates = [start + timedelta(days=i) for i in range(days)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": [100.0 + i * 0.1 for i in range(days)],
            "high": [105.0 + i * 0.1 for i in range(days)],
            "low": [95.0 + i * 0.1 for i in range(days)],
            "close": [102.0 + i * 0.1 for i in range(days)],
            "volume": [1000 * (i + 1) for i in range(days)],
        }
    )


class TestDaemonIntegration:
    @pytest.mark.asyncio
    async def test_run_once_full_pipeline(self, tmp_path):
        """Full pipeline: fetch + analyze for a watchlist."""
        db_path = str(tmp_path / "test.db")
        config = CaracalConfig(db_path=db_path)
        service = DaemonService(config, pid_dir=tmp_path)

        # Set up: create watchlist and mock provider
        from caracal.storage.duckdb import DuckDBStorage

        storage = DuckDBStorage(db_path)
        storage.create_watchlist("test")
        storage.add_to_watchlist("test", "AAPL")
        storage.close()

        mock_provider = MagicMock()
        mock_provider.fetch_ohlcv.return_value = _make_ohlcv()

        with patch(
            "caracal.daemon.tasks.fetch.get_provider",
            return_value=mock_provider,
        ):
            results = await service.run_once()

        # FetchTask should succeed
        assert results[0].status == "ok"
        assert results[0].items_processed == 1

        # AnalysisTask should succeed (data now exists)
        assert results[1].status == "ok"
        assert results[1].items_processed == 1

        # Verify data persisted
        storage = DuckDBStorage(db_path)
        ohlcv = storage.get_ohlcv("AAPL")
        assert not ohlcv.empty
        indicators = storage.get_indicators("AAPL")
        assert not indicators.empty
        storage.close()

import pytest

from caracal.storage.duckdb import DuckDBStorage


@pytest.fixture
def storage():
    """In-memory DuckDB storage for daemon tests."""
    s = DuckDBStorage(":memory:")
    yield s
    s.close()

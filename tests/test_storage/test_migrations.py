import duckdb
import pytest
from caracal.storage.migrations import get_schema_version, run_migrations, CURRENT_VERSION


class TestMigrations:
    def test_fresh_db_gets_current_version(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = duckdb.connect(db_path)
        run_migrations(conn)
        assert get_schema_version(conn) == CURRENT_VERSION
        conn.close()

    def test_legacy_db_without_version_table_migrates(self, tmp_path):
        """Simulate a pre-migration DB (has ohlcv table but no schema_version)."""
        db_path = str(tmp_path / "test.db")
        conn = duckdb.connect(db_path)
        conn.execute("CREATE TABLE ohlcv (ticker VARCHAR, date DATE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT, PRIMARY KEY (ticker, date))")
        conn.execute("CREATE TABLE indicators (ticker VARCHAR, date DATE, name VARCHAR, value DOUBLE, PRIMARY KEY (ticker, date, name))")
        conn.execute("CREATE TABLE watchlists (name VARCHAR PRIMARY KEY, created_at TIMESTAMP DEFAULT current_timestamp)")
        conn.execute("CREATE TABLE watchlist_items (watchlist_name VARCHAR, ticker VARCHAR, added_at TIMESTAMP DEFAULT current_timestamp, PRIMARY KEY (watchlist_name, ticker))")
        conn.execute("CREATE TABLE ticker_metadata (ticker VARCHAR PRIMARY KEY, name VARCHAR)")
        # No schema_version table — legacy DB
        run_migrations(conn)
        assert get_schema_version(conn) == CURRENT_VERSION
        conn.close()

    def test_idempotent_migration(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = duckdb.connect(db_path)
        run_migrations(conn)
        run_migrations(conn)  # Should not fail
        assert get_schema_version(conn) == CURRENT_VERSION
        conn.close()

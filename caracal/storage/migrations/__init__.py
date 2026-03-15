"""Schema migration framework for DuckDB."""

from __future__ import annotations

import logging

import duckdb

logger = logging.getLogger("caracal")

CURRENT_VERSION = 3


def get_schema_version(conn: duckdb.DuckDBPyConnection) -> int:
    """Return current schema version, 0 if no version table exists."""
    try:
        result = conn.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        ).fetchone()
        return result[0] if result else 0
    except duckdb.CatalogException:
        return 0


def _ensure_version_table(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version ("
        "  version INTEGER NOT NULL,"
        "  applied_at TIMESTAMP DEFAULT current_timestamp"
        ")"
    )


def _detect_legacy_db(conn: duckdb.DuckDBPyConnection) -> bool:
    """Check if DB has tables but no schema_version (pre-migration)."""
    try:
        conn.execute("SELECT 1 FROM ohlcv LIMIT 0")
        return True
    except duckdb.CatalogException:
        return False


def run_migrations(conn: duckdb.DuckDBPyConnection) -> None:
    """Run all pending migrations."""
    _ensure_version_table(conn)
    current = get_schema_version(conn)

    if current == 0 and _detect_legacy_db(conn):
        # Legacy DB — tables exist but no version tracking
        logger.info("Legacy database detected, setting version to 1")
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", [1])
        current = 1

    if current == 0:
        # Fresh DB — run initial schema
        from caracal.storage.migrations._001_initial import migrate

        migrate(conn)
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", [1])
        logger.info("Applied migration 001_initial")

    if current < 2:
        from caracal.storage.migrations._002_worker_runs import migrate as migrate_002

        migrate_002(conn)
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", [2])
        logger.info("Applied migration 002_worker_runs")

    if current < 3:
        from caracal.storage.migrations._003_news import migrate as migrate_003

        migrate_003(conn)
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", [3])
        logger.info("Applied migration 003_news")

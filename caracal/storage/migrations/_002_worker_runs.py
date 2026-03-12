"""Migration 002: worker_runs table for daemon task tracking."""

import duckdb


def migrate(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS worker_runs (
            task_name VARCHAR NOT NULL,
            started_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            status VARCHAR NOT NULL,
            message VARCHAR,
            items_processed INTEGER DEFAULT 0,
            PRIMARY KEY (task_name, started_at)
        )
    """)

"""Migration 003: news table for RSS news storage."""

import duckdb


def migrate(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id           VARCHAR PRIMARY KEY,
            source       VARCHAR NOT NULL,
            feed         VARCHAR NOT NULL,
            headline     VARCHAR NOT NULL,
            summary      VARCHAR,
            url          VARCHAR,
            published_at TIMESTAMP NOT NULL,
            fetched_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

"""Migration 001: Initial schema (retroactive for v1.0-v1.3)."""

import duckdb


def migrate(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            ticker VARCHAR NOT NULL,
            date DATE NOT NULL,
            open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
            volume BIGINT,
            PRIMARY KEY (ticker, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            ticker VARCHAR NOT NULL,
            date DATE NOT NULL,
            name VARCHAR NOT NULL,
            value DOUBLE,
            PRIMARY KEY (ticker, date, name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlists (
            name VARCHAR NOT NULL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT current_timestamp
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist_items (
            watchlist_name VARCHAR NOT NULL,
            ticker VARCHAR NOT NULL,
            added_at TIMESTAMP DEFAULT current_timestamp,
            PRIMARY KEY (watchlist_name, ticker),
            FOREIGN KEY (watchlist_name) REFERENCES watchlists(name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ticker_metadata (
            ticker VARCHAR NOT NULL PRIMARY KEY,
            name VARCHAR
        )
    """)

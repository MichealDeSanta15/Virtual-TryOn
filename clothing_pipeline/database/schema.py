"""
SQLite schema creation and initialization.
"""

import sqlite3
import logging
from pathlib import Path

from clothing_pipeline.config import DB_PATH, DB_JOURNAL_MODE

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
-- ── Products table ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    source_url      TEXT UNIQUE,
    title           TEXT NOT NULL,
    brand           TEXT,
    price           REAL,
    currency        TEXT DEFAULT 'INR',
    category        TEXT,
    color           TEXT,
    occasion        TEXT,
    sizes           TEXT,
    image_path      TEXT,
    image_url       TEXT,
    metadata        TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── Scrape log ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scrape_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    query           TEXT NOT NULL,
    source          TEXT NOT NULL,
    status          TEXT,
    items_found     INTEGER DEFAULT 0,
    error_message   TEXT,
    duration_ms     INTEGER,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── Cache entries ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cache_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key       TEXT UNIQUE NOT NULL,
    result_ids      TEXT NOT NULL,
    hit_count       INTEGER DEFAULT 0,
    last_accessed   DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ── Indexes ─────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_products_brand      ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_category   ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_price      ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_occasion   ON products(occasion);
CREATE INDEX IF NOT EXISTS idx_products_color      ON products(color);
CREATE INDEX IF NOT EXISTS idx_products_source     ON products(source);
CREATE INDEX IF NOT EXISTS idx_cache_last_accessed ON cache_entries(last_accessed);
CREATE INDEX IF NOT EXISTS idx_scrape_log_query    ON scrape_log(query);
"""


def initialize_database(db_path: Path | None = None) -> sqlite3.Connection:
    """
    Create the SQLite database and tables if they don't exist.

    Args:
        db_path: Optional override for the database file path.

    Returns:
        An open sqlite3.Connection with row_factory = sqlite3.Row.
    """
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Initializing database at %s", path)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=%s" % DB_JOURNAL_MODE)
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript(SCHEMA_SQL)
    conn.commit()

    logger.info("Database initialized successfully")
    return conn


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """
    Get a connection to the database (creates tables if needed).
    """
    return initialize_database(db_path)

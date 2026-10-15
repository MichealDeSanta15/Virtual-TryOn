"""
CRUD operations for the products database.
"""

import sqlite3
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from clothing_pipeline.database.models import Product, ScrapeLog
from clothing_pipeline.database.schema import get_connection
from clothing_pipeline.config import DB_PATH

logger = logging.getLogger(__name__)


class ProductDB:
    """
    Database access layer for clothing products.

    Thread-safe: each method opens and closes its own connection,
    or you can inject one via the constructor for batch operations.
    """

    def __init__(self, conn: Optional[sqlite3.Connection] = None, db_path=None):
        self.db_path = Path(db_path or DB_PATH)
        self._conn = conn
        self._owns_conn = conn is None
        if conn is None:
            initial = get_connection(self.db_path)
            initial.close()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        conn = sqlite3.connect(str(self.db_path), timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=15000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _close_if_owned(self, conn: sqlite3.Connection):
        if self._owns_conn and conn is not self._conn:
            conn.close()

    # ── Insert / Upsert ──────────────────────────────────────────────────

    def insert_product(self, product: Product) -> int:
        """
        Insert a product. If source_url already exists, update instead.
        Returns the product ID.
        """
        conn = self._get_conn()
        try:
            if not product.source_url or not product.title:
                raise ValueError("Product needs a unique source_url and title")
            row = product.to_db_row()
            cursor = conn.execute(
                """
                INSERT INTO products
                    (source, source_url, title, brand, price, currency,
                     category, color, occasion, sizes, image_path,
                     image_url, metadata)
                VALUES
                    (:source, :source_url, :title, :brand, :price, :currency,
                     :category, :color, :occasion, :sizes, :image_path,
                     :image_url, :metadata)
                ON CONFLICT(source_url) DO UPDATE SET
                    title      = excluded.title,
                    brand      = excluded.brand,
                    price      = excluded.price,
                    currency   = excluded.currency,
                    category   = excluded.category,
                    color      = excluded.color,
                    occasion   = excluded.occasion,
                    sizes      = excluded.sizes,
                    image_path = COALESCE(excluded.image_path, products.image_path),
                    image_url  = excluded.image_url,
                    metadata   = excluded.metadata,
                    updated_at = CURRENT_TIMESTAMP
                """,
                row,
            )
            conn.commit()
            return conn.execute("SELECT id FROM products WHERE source_url=?", (product.source_url,)).fetchone()[0]
        finally:
            self._close_if_owned(conn)

    def bulk_insert(self, products: List[Product]) -> List[int]:
        """Insert multiple products in a single transaction."""
        conn = self._get_conn()
        try:
            ids = []
            for product in products:
                if not product.source_url or not product.title:
                    raise ValueError("Product needs a unique source_url and title")
                row = product.to_db_row()
                cursor = conn.execute(
                    """
                    INSERT INTO products
                        (source, source_url, title, brand, price, currency,
                         category, color, occasion, sizes, image_path,
                         image_url, metadata)
                    VALUES
                        (:source, :source_url, :title, :brand, :price,
                         :currency, :category, :color, :occasion, :sizes,
                         :image_path, :image_url, :metadata)
                    ON CONFLICT(source_url) DO UPDATE SET
                        title      = excluded.title,
                        brand      = excluded.brand,
                        price      = excluded.price,
                    currency   = excluded.currency,
                        category   = excluded.category,
                        color      = excluded.color,
                        occasion   = excluded.occasion,
                        sizes      = excluded.sizes,
                        image_path = COALESCE(excluded.image_path, products.image_path),
                        image_url  = excluded.image_url,
                        metadata   = excluded.metadata,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    row,
                )
                ids.append(conn.execute("SELECT id FROM products WHERE source_url=?", (product.source_url,)).fetchone()[0])
            conn.commit()
            return ids
        finally:
            self._close_if_owned(conn)

    # ── Queries ──────────────────────────────────────────────────────────

    def get_product_by_id(self, product_id: int) -> Optional[Product]:
        """Fetch a single product by ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            )
            row = cursor.fetchone()
            if row:
                return Product.from_db_row(dict(row))
            return None
        finally:
            self._close_if_owned(conn)

    def get_products_by_ids(self, ids: List[int]) -> List[Product]:
        """Fetch multiple products by their IDs, preserving order."""
        if not ids:
            return []
        conn = self._get_conn()
        try:
            placeholders = ",".join("?" for _ in ids)
            cursor = conn.execute(
                f"SELECT * FROM products WHERE id IN ({placeholders})", ids
            )
            rows = cursor.fetchall()
            products_map = {
                dict(r)["id"]: Product.from_db_row(dict(r)) for r in rows
            }
            return [products_map[pid] for pid in ids if pid in products_map]
        finally:
            self._close_if_owned(conn)

    def search_products(
        self,
        query: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        occasion: Optional[str] = None,
        color: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Product]:
        """
        Search products with filters.

        Args:
            query: Free-text search against title.
            min_price / max_price: Price range filter.
            brand: Exact brand match (case-insensitive).
            category: Exact category match.
            occasion: Exact occasion match.
            color: Partial color match (case-insensitive).
            source: Filter by source site.
            limit: Max results to return.
            offset: Pagination offset.

        Returns:
            List of matching Product objects.
        """
        conn = self._get_conn()
        try:
            conditions = []
            params: List[Any] = []

            if query:
                conditions.append("title LIKE ?")
                params.append(f"%{query}%")

            if min_price is not None:
                conditions.append("price >= ?")
                params.append(min_price)

            if max_price is not None:
                conditions.append("price <= ?")
                params.append(max_price)

            if brand:
                conditions.append("LOWER(brand) = LOWER(?)")
                params.append(brand)

            if category:
                conditions.append("LOWER(category) = LOWER(?)")
                params.append(category)

            if occasion:
                conditions.append("LOWER(occasion) = LOWER(?)")
                params.append(occasion)

            if color:
                conditions.append("LOWER(color) LIKE LOWER(?)")
                params.append(f"%{color}%")

            if source:
                conditions.append("source = ?")
                params.append(source)

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            sql = f"""
                SELECT * FROM products
                {where_clause}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            return [Product.from_db_row(dict(r)) for r in rows]
        finally:
            self._close_if_owned(conn)

    def count_products(self, **filters) -> int:
        """Count products matching the given filters."""
        conn = self._get_conn()
        try:
            conditions = []
            params: List[Any] = []

            allowed = {"source", "brand", "category", "occasion", "color", "currency"}
            if set(filters) - allowed:
                raise ValueError("Unknown product filter")
            for key, val in filters.items():
                if val is not None:
                    conditions.append(f"LOWER({key}) = LOWER(?)")
                    params.append(val)

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            cursor = conn.execute(
                f"SELECT COUNT(*) FROM products {where_clause}", params
            )
            return cursor.fetchone()[0]
        finally:
            self._close_if_owned(conn)

    # ── Scrape Log ───────────────────────────────────────────────────────

    def log_scrape(self, log: ScrapeLog) -> int:
        """Record a scraping operation in the log."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """
                INSERT INTO scrape_log
                    (query, source, status, items_found,
                     error_message, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    log.query,
                    log.source,
                    log.status,
                    log.items_found,
                    log.error_message,
                    log.duration_ms,
                ),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            self._close_if_owned(conn)

    # ── Cache Operations ─────────────────────────────────────────────────

    def get_cache_entry(self, cache_key: str) -> Optional[Dict]:
        """Retrieve a cache entry and bump its hit count + access time."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM cache_entries WHERE cache_key = ?",
                (cache_key,),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            # Bump hit count and last_accessed
            conn.execute(
                """
                UPDATE cache_entries
                SET hit_count = hit_count + 1,
                    last_accessed = CURRENT_TIMESTAMP
                WHERE cache_key = ?
                """,
                (cache_key,),
            )
            conn.commit()

            row_dict = dict(row)
            row_dict["result_ids"] = json.loads(row_dict["result_ids"])
            return row_dict
        finally:
            self._close_if_owned(conn)

    def set_cache_entry(self, cache_key: str, result_ids: List[int]):
        """Create or update a cache entry."""
        conn = self._get_conn()
        try:
            conn.execute(
                """
                INSERT INTO cache_entries (cache_key, result_ids)
                VALUES (?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    result_ids = excluded.result_ids,
                    hit_count = hit_count + 1,
                    last_accessed = CURRENT_TIMESTAMP,
                    created_at = CURRENT_TIMESTAMP
                """,
                (cache_key, json.dumps(result_ids)),
            )
            conn.commit()
        finally:
            self._close_if_owned(conn)

    def evict_lru_cache(self, max_entries: int):
        """Remove least-recently-used cache entries beyond max_entries."""
        conn = self._get_conn()
        try:
            conn.execute(
                """
                DELETE FROM cache_entries
                WHERE id NOT IN (
                    SELECT id FROM cache_entries
                    ORDER BY last_accessed DESC, id DESC
                    LIMIT ?
                )
                """,
                (max_entries,),
            )
            conn.commit()
        finally:
            self._close_if_owned(conn)

    def cache_entry_count(self) -> int:
        """Return number of cache entries."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM cache_entries")
            return cursor.fetchone()[0]
        finally:
            self._close_if_owned(conn)

    def clear_cache(self):
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM cache_entries")
            conn.commit()
        finally:
            self._close_if_owned(conn)

    def delete_cache_entry(self, key):
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM cache_entries WHERE cache_key=?", (key,))
            conn.commit()
        finally:
            self._close_if_owned(conn)

    # ── Cleanup ──────────────────────────────────────────────────────────

    def close(self):
        """Close the underlying connection if we own it."""
        if self._conn is not None and not self._owns_conn:
            pass  # caller owns it
        elif self._conn is not None:
            self._conn.close()
            self._conn = None

import os
import sys
import sqlite3
import tempfile
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from clothing_pipeline.database.schema import initialize_database
from clothing_pipeline.database.operations import ProductDB
from clothing_pipeline.database.models import Product, ScrapeLog


def test_schema_creation():
    """Test that all tables and indexes are created."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = initialize_database(db_path)

        # Check tables exist
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "ORDER BY name"
        )
        tables = {row["name"] for row in cursor.fetchall()}
        assert "products" in tables
        assert "scrape_log" in tables
        assert "cache_entries" in tables

        # Check indexes
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indexes = {row["name"] for row in cursor.fetchall()}
        assert "idx_products_brand" in indexes
        assert "idx_products_price" in indexes

        conn.close()
        import gc; gc.collect()
        print("✓ test_schema_creation passed")


def test_product_insert_and_query():
    """Test inserting and querying products."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = initialize_database(db_path)
        db = ProductDB(conn)

        # Insert a product
        p = Product(
            source="myntra",
            source_url="https://myntra.com/test-product-1",
            title="Blue Denim Shirt",
            brand="Levi's",
            price=1999.0,
            category="shirt",
            color="blue",
            occasion="casual",
            sizes=["S", "M", "L"],
        )
        pid = db.insert_product(p)
        assert pid > 0

        # Query by ID
        result = db.get_product_by_id(pid)
        assert result is not None
        assert result.title == "Blue Denim Shirt"
        assert result.brand == "Levi's"
        assert result.price == 1999.0
        assert result.sizes == ["S", "M", "L"]

        conn.close()
        import gc; gc.collect()
        print("✓ test_product_insert_and_query passed")


def test_search_products():
    """Test search with various filters."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = initialize_database(db_path)
        db = ProductDB(conn)

        # Insert test data
        products = [
            Product(source="myntra", source_url="https://m.com/1",
                    title="Red Party Dress", brand="Zara",
                    price=3500, category="dress", color="red",
                    occasion="party"),
            Product(source="ajio", source_url="https://a.com/2",
                    title="Blue Formal Blazer", brand="Raymond",
                    price=5000, category="blazer", color="blue",
                    occasion="wedding"),
            Product(source="amazon", source_url="https://az.com/3",
                    title="White Cotton Shirt", brand="Van Heusen",
                    price=1200, category="shirt", color="white",
                    occasion="formal"),
        ]
        db.bulk_insert(products)

        # Search by price range
        results = db.search_products(min_price=1000, max_price=4000)
        assert len(results) == 2  # dress and shirt

        # Search by brand
        results = db.search_products(brand="zara")
        assert len(results) == 1
        assert results[0].title == "Red Party Dress"

        # Search by occasion
        results = db.search_products(occasion="wedding")
        assert len(results) == 1
        assert results[0].brand == "Raymond"

        # Search by text query
        results = db.search_products(query="Cotton")
        assert len(results) == 1
        assert "Cotton" in results[0].title

        conn.close()
        import gc; gc.collect()
        print("✓ test_search_products passed")


def test_upsert():
    """Test that duplicate source_url triggers update."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = initialize_database(db_path)
        db = ProductDB(conn)

        p1 = Product(source="myntra", source_url="https://m.com/dup",
                     title="Original Title", price=1000)
        db.insert_product(p1)

        p2 = Product(source="myntra", source_url="https://m.com/dup",
                     title="Updated Title", price=1500)
        db.insert_product(p2)

        # Should only have one product
        results = db.search_products(source="myntra")
        assert len(results) == 1
        assert results[0].title == "Updated Title"
        assert results[0].price == 1500

        conn.close()
        import gc; gc.collect()
        print("✓ test_upsert passed")


def test_cache_operations():
    """Test cache set/get/evict."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = initialize_database(db_path)
        db = ProductDB(conn)

        # Set cache
        db.set_cache_entry("key1", [1, 2, 3])
        db.set_cache_entry("key2", [4, 5])

        # Get cache
        entry = db.get_cache_entry("key1")
        assert entry is not None
        assert entry["result_ids"] == [1, 2, 3]

        # Hit count should be bumped (was 0, first get bumped to 1, second get bumps to 2)
        entry2 = db.get_cache_entry("key1")
        assert entry2["hit_count"] >= 1

        # Miss
        entry3 = db.get_cache_entry("nonexistent")
        assert entry3 is None

        # Evict — keep only 1
        db.evict_lru_cache(1)
        count = db.cache_entry_count()
        assert count == 1

        conn.close()
        # Ensure all connections are fully released on Windows
        import gc; gc.collect()
        print("✓ test_cache_operations passed")


def test_scrape_log():
    """Test scrape logging."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = initialize_database(db_path)
        db = ProductDB(conn)

        log = ScrapeLog(
            query="wedding dress",
            source="myntra",
            status="success",
            items_found=15,
            duration_ms=3200,
        )
        log_id = db.log_scrape(log)
        assert log_id > 0

        conn.close()
        import gc; gc.collect()
        print("✓ test_scrape_log passed")


if __name__ == "__main__":
    test_schema_creation()
    test_product_insert_and_query()
    test_search_products()
    test_upsert()
    test_cache_operations()
    test_scrape_log()
    print("\n✅ All database tests passed!")

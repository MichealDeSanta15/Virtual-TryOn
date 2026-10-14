import os
import sys
import tempfile
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Override DB path before importing api
os.environ["CLOTHING_PIPELINE_TEST"] = "1"

from clothing_pipeline.database.schema import initialize_database
from clothing_pipeline.database.operations import ProductDB
from clothing_pipeline.database.models import Product
from clothing_pipeline.search.engine import SearchEngine
from clothing_pipeline.cache.lru_cache import QueryCache
from clothing_pipeline.fallback.loader import FallbackDataset


def test_fallback_search():
    """Test that fallback returns results when DB is empty."""
    fallback = FallbackDataset()

    # Wedding items
    results = fallback.search(occasion="wedding")
    assert len(results) > 0
    for r in results:
        assert r.occasion in ("wedding",)
    print(f"✓ test_fallback_search: {len(results)} wedding items")


def test_fallback_price_filter():
    """Test fallback price filtering."""
    fallback = FallbackDataset()

    results = fallback.search(max_price=2000)
    assert len(results) > 0
    for r in results:
        assert r.price <= 2000
    print(f"✓ test_fallback_price_filter: {len(results)} items under ₹2000")


def test_end_to_end_with_db():
    """Test the full flow: insert → search → cache."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = initialize_database(db_path)
        db = ProductDB(conn)
        cache = QueryCache(db)
        engine = SearchEngine(db, cache)

        # Populate DB with products that have occasion tags
        products = [
            Product(
                source="myntra",
                source_url="https://m.com/wedding1",
                title="Royal Blue Sherwani",
                brand="Manyavar",
                price=6999,
                category="sherwani",
                occasion="wedding",
                color="blue",
            ),
            Product(
                source="ajio",
                source_url="https://a.com/wedding2",
                title="Gold Embroidered Lehenga",
                brand="Kalki",
                price=12999,
                category="lehenga",
                occasion="wedding",
                color="gold",
            ),
            Product(
                source="myntra",
                source_url="https://m.com/casual1",
                title="Grey Hoodie",
                brand="H&M",
                price=1499,
                category="hoodie",
                occasion="casual",
                color="grey",
            ),
        ]
        db.bulk_insert(products)

        # Search by occasion directly from DB — should find wedding items
        results = db.search_products(occasion="wedding", max_price=10000)
        assert len(results) >= 1
        titles = [r.title for r in results]
        assert "Royal Blue Sherwani" in titles
        # Lehenga (₹12999) should be filtered out by max_price=10000
        assert "Gold Embroidered Lehenga" not in titles
        print(f"✓ test_end_to_end_with_db: found {len(results)} results")

        # Test cache round-trip
        cache.put({"test": "wedding"}, [r.id for r in results])
        cached_ids = cache.get({"test": "wedding"})
        assert cached_ids is not None
        assert len(cached_ids) >= 1
        print("✓ test_end_to_end_with_db: cache round-trip verified")

        conn.close()
        import gc; gc.collect()


def test_fallback_category_filter():
    """Test fallback category filtering."""
    fallback = FallbackDataset()

    results = fallback.search(category="shirt")
    assert len(results) > 0
    for r in results:
        assert "shirt" in r.category.lower()
    print(f"✓ test_fallback_category_filter: {len(results)} shirts")


if __name__ == "__main__":
    test_fallback_search()
    test_fallback_price_filter()
    test_fallback_category_filter()
    test_end_to_end_with_db()
    print("\n✅ All API tests passed!")

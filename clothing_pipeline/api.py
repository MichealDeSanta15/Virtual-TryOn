"""
Public API for the clothing data pipeline.

Usage:
    from clothing_pipeline.api import search_clothes

    results = search_clothes(event="wedding", budget="5000")
    for item in results:
        print(item["title"], item["price"], item["image_path"])
"""

import asyncio
import logging
from typing import List, Dict, Optional, Any

from clothing_pipeline.database.schema import initialize_database
from clothing_pipeline.database.operations import ProductDB
from clothing_pipeline.cache.lru_cache import QueryCache
from clothing_pipeline.search.engine import SearchEngine
from clothing_pipeline.scraper import ScraperOrchestrator
from clothing_pipeline.fallback.loader import FallbackDataset

logger = logging.getLogger(__name__)

# Module-level singletons (lazy-initialized)
_db: Optional[ProductDB] = None
_search_engine: Optional[SearchEngine] = None
_fallback: Optional[FallbackDataset] = None


def _init():
    """Lazy-initialize the database, search engine, and fallback."""
    global _db, _search_engine, _fallback
    if _db is None:
        conn = initialize_database()
        _db = ProductDB(conn)
        cache = QueryCache(_db)
        _search_engine = SearchEngine(_db, cache)
        _fallback = FallbackDataset()
        logger.info("Clothing pipeline initialized")


def search_clothes(
    event: str,
    budget: str,
    *,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    color: Optional[str] = None,
    source: Optional[str] = None,
    scrape_if_empty: bool = True,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Search for clothing items matching an event and budget.

    This is the main entry point for the clothing pipeline. It:
    1. Checks the local cache/database for matching products.
    2. If empty and scrape_if_empty is True, triggers live scraping.
    3. Falls back to the bundled demo dataset if all else fails.

    Args:
        event: The occasion (e.g., 'wedding', 'party', 'interview',
               'casual', 'date', 'festival', 'gym', 'beach').
        budget: Budget string — e.g., '5000', '2000-5000', 'under 3000'.
        brand: Optional brand filter.
        category: Optional category filter (e.g., 'blazer', 'dress').
        color: Optional color filter.
        source: Optional source filter ('myntra', 'ajio', 'amazon').
        scrape_if_empty: Whether to trigger live scraping if DB is empty.
        limit: Maximum number of results.

    Returns:
        List of dicts, each containing:
        - id, title, brand, price, category, color, occasion
        - image_path (local file path for the try-on engine)
        - source, source_url
    """
    _init()

    logger.info(
        "search_clothes(event=%r, budget=%r, brand=%r, "
        "category=%r, color=%r, source=%r)",
        event, budget, brand, category, color, source,
    )

    # ── Step 1: Search local DB / cache ──────────────────────────────
    results = _search_engine.search(
        event=event,
        budget=budget,
        brand=brand,
        category=category,
        color=color,
        source=source,
        limit=limit,
    )

    if results:
        logger.info("Found %d results from local DB", len(results))
        return [p.to_dict() for p in results]

    # ── Step 2: Live scraping ────────────────────────────────────────
    if scrape_if_empty:
        logger.info("No local results — triggering live scraping")
        try:
            scraped = _run_scraping(event)
            if scraped:
                # Re-run the search now that DB is populated
                results = _search_engine.search(
                    event=event,
                    budget=budget,
                    brand=brand,
                    category=category,
                    color=color,
                    source=source,
                    limit=limit,
                )
                if results:
                    logger.info(
                        "Found %d results after scraping", len(results)
                    )
                    return [p.to_dict() for p in results]
        except Exception as e:
            logger.error("Scraping failed: %s", str(e), exc_info=True)

    # ── Step 3: Fallback dataset ─────────────────────────────────────
    logger.info("Using fallback dataset")
    min_price, max_price = _search_engine.parse_budget(budget)
    occasion_info = _search_engine.get_occasion_info(event)

    fallback_results = _fallback.search(
        occasion=occasion_info["occasion_tag"],
        min_price=min_price,
        max_price=max_price,
        category=category,
        color=color,
        limit=limit,
    )

    # If occasion filter returned nothing, try without it
    if not fallback_results:
        fallback_results = _fallback.search(
            min_price=min_price,
            max_price=max_price,
            limit=limit,
        )

    logger.info("Returning %d fallback results", len(fallback_results))
    return [p.to_dict() for p in fallback_results]


def _run_scraping(event: str) -> List:
    """
    Run the scraper orchestrator synchronously.

    Handles the async → sync bridge for callers that aren't in an
    async context.
    """
    orchestrator = ScraperOrchestrator(db=_db)
    keywords = _search_engine.get_search_keywords(event)

    all_products = []

    # Use the first 2 keywords to avoid over-scraping
    keywords_to_try = keywords[:2] if keywords else [event]

    for keyword in keywords_to_try:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                products = loop.run_until_complete(
                    orchestrator.scrape_all(keyword)
                )
                all_products.extend(products)
            finally:
                loop.close()
        except Exception as e:
            logger.error(
                "Scraping failed for keyword '%s': %s",
                keyword,
                str(e),
            )

    return all_products


# ── Convenience Functions ────────────────────────────────────────────────

def get_product(product_id: int) -> Optional[Dict]:
    """Fetch a single product by ID."""
    _init()
    product = _db.get_product_by_id(product_id)
    if product:
        return product.to_dict()
    return None


def clear_cache():
    """Clear the search cache."""
    _init()
    cache = QueryCache(_db)
    cache.clear()
    logger.info("Cache cleared via API")


def get_stats() -> Dict[str, Any]:
    """Get pipeline statistics."""
    _init()
    return {
        "total_products": _db.count_products(),
        "cache_entries": _db.cache_entry_count(),
        "sources": {
            "myntra": _db.count_products(source="myntra"),
            "ajio": _db.count_products(source="ajio"),
            "amazon": _db.count_products(source="amazon"),
            "fallback": len(_fallback.get_all()) if _fallback else 0,
        },
    }

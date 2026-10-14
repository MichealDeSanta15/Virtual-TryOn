"""
Search engine — query products with filters, occasion mapping, and budget parsing.
"""

import logging
import re
from typing import List, Optional, Dict, Any

from clothing_pipeline.database.models import Product
from clothing_pipeline.database.operations import ProductDB
from clothing_pipeline.cache.lru_cache import QueryCache
from clothing_pipeline.config import OCCASION_MAP, DEFAULT_OCCASION

logger = logging.getLogger(__name__)


class SearchEngine:
    """
    Search products from the local database with rich filtering.

    Integrates with the LRU cache for repeated queries.
    """

    def __init__(
        self,
        db: Optional[ProductDB] = None,
        cache: Optional[QueryCache] = None,
    ):
        self.db = db or ProductDB()
        self.cache = cache or QueryCache(self.db)

    # ── Budget Parsing ───────────────────────────────────────────────────

    @staticmethod
    def parse_budget(budget: str) -> tuple[Optional[float], Optional[float]]:
        """
        Parse a budget string into (min_price, max_price).

        Supported formats:
            "5000"         → (None, 5000)
            "₹5000"        → (None, 5000)
            "2000-5000"    → (2000, 5000)
            "1000 to 3000" → (1000, 3000)
            "under 2000"   → (None, 2000)
            "above 3000"   → (3000, None)
        """
        if not budget:
            return None, None

        budget = budget.strip()
        # Remove currency symbols
        budget = re.sub(r"[₹$,Rs.\s]", " ", budget).strip()

        # "under X" or "below X"
        match = re.match(r"(?:under|below|max|upto|up\s*to)\s*(\d+)", budget, re.I)
        if match:
            return None, float(match.group(1))

        # "above X" or "over X" or "min X"
        match = re.match(r"(?:above|over|min|from)\s*(\d+)", budget, re.I)
        if match:
            return float(match.group(1)), None

        # "X-Y" or "X to Y"
        match = re.match(r"(\d+)\s*[-–—to]+\s*(\d+)", budget, re.I)
        if match:
            lo, hi = float(match.group(1)), float(match.group(2))
            return (min(lo, hi), max(lo, hi))

        # Plain number → treat as max budget
        match = re.match(r"(\d+)", budget)
        if match:
            return None, float(match.group(1))

        return None, None

    # ── Occasion → Search Keywords ───────────────────────────────────────

    @staticmethod
    def get_occasion_info(event: str) -> Dict[str, Any]:
        """
        Map an event name to occasion metadata (keywords, tag, categories).
        """
        event_lower = event.lower().strip()

        # Direct match
        if event_lower in OCCASION_MAP:
            return OCCASION_MAP[event_lower]

        # Partial match
        for key, info in OCCASION_MAP.items():
            if key in event_lower or event_lower in key:
                return info

        # Fallback: use the event as a keyword
        return {
            **DEFAULT_OCCASION,
            "keywords": [event, f"{event} outfit", f"{event} wear"],
            "occasion_tag": event_lower,
        }

    # ── Main Search ──────────────────────────────────────────────────────

    def search(
        self,
        event: Optional[str] = None,
        budget: Optional[str] = None,
        brand: Optional[str] = None,
        category: Optional[str] = None,
        color: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 50,
        use_cache: bool = True,
    ) -> List[Product]:
        """
        Search for products matching the given criteria.

        Args:
            event: Occasion/event (e.g., 'wedding', 'party', 'interview').
            budget: Budget string (see parse_budget for formats).
            brand: Filter by brand name.
            category: Filter by clothing category.
            color: Filter by color.
            source: Filter by source ('myntra', 'ajio', 'amazon').
            limit: Max results.
            use_cache: Whether to check the query cache.

        Returns:
            List of matching Product objects, sorted by relevance.
        """
        # Parse budget
        min_price, max_price = self.parse_budget(budget or "")

        # Map event to occasion tag
        occasion = None
        search_query = None
        if event:
            occasion_info = self.get_occasion_info(event)
            occasion = occasion_info["occasion_tag"]
            # Use first keyword as the text search query
            if occasion_info["keywords"]:
                search_query = occasion_info["keywords"][0]

        # Build cache key params
        cache_params = {
            "query": search_query,
            "event": event,
            "min_price": min_price,
            "max_price": max_price,
            "brand": brand,
            "category": category,
            "occasion": occasion,
            "color": color,
            "source": source,
            "limit": limit,
        }

        # Check cache
        if use_cache:
            cached_ids = self.cache.get(cache_params)
            if cached_ids:
                products = self.db.get_products_by_ids(cached_ids)
                if products:
                    logger.info(
                        "Returning %d cached results for event='%s'",
                        len(products),
                        event,
                    )
                    return products

        # Query database
        products = self.db.search_products(
            query=search_query,
            min_price=min_price,
            max_price=max_price,
            brand=brand,
            category=category,
            occasion=occasion,
            color=color,
            source=source,
            limit=limit,
        )

        # If no results with occasion filter, try without it
        if not products and occasion:
            products = self.db.search_products(
                query=search_query,
                min_price=min_price,
                max_price=max_price,
                brand=brand,
                category=category,
                color=color,
                source=source,
                limit=limit,
            )

        # If still no results, try just the title search
        if not products and search_query:
            products = self.db.search_products(
                query=search_query,
                min_price=min_price,
                max_price=max_price,
                limit=limit,
            )

        # Cache the results
        if products and use_cache:
            product_ids = [p.id for p in products if p.id is not None]
            if product_ids:
                self.cache.put(cache_params, product_ids)

        logger.info(
            "Search returned %d results for event='%s', budget='%s'",
            len(products),
            event,
            budget,
        )
        return products

    def get_search_keywords(self, event: str) -> List[str]:
        """
        Get the scraping keywords for a given event.
        Used by the API to decide what to scrape.
        """
        info = self.get_occasion_info(event)
        return info["keywords"]

"""
Scraper module interface for Friend 1's PyQt6 GUI.
Connects the GUI directly to Friend 2's Web Scraping & Data Management pipeline.
"""
from typing import List, Dict, Any
import logging
from clothing_pipeline.api import search_clothes as pipeline_search

logger = logging.getLogger(__name__)


def search_clothes(event_text: str, budget_text: str) -> List[Dict[str, Any]]:
    """
    Search clothing items matching event and budget using Friend 2's pipeline.
    Formats price and ensures image_path is ready for UI display & try-on.
    """
    try:
        raw_results = pipeline_search(
            event=event_text,
            budget=budget_text,
            scrape_if_empty=False,  # instant response via DB / curated fallback
            limit=20,
        )

        formatted_items = []
        for item in raw_results:
            price_val = item.get("price", 0)
            formatted_price = f"₹{int(price_val):,}" if isinstance(price_val, (int, float)) else str(price_val)

            formatted_items.append({
                "id": str(item.get("id", "")),
                "title": item.get("title", "Clothing Item"),
                "brand": item.get("brand", "Generic"),
                "price": formatted_price,
                "category": item.get("category", ""),
                "color": item.get("color", ""),
                "occasion": item.get("occasion", ""),
                "image_path": item.get("image_path", ""),
                "source": item.get("source", "clothing_pipeline"),
                "source_url": item.get("source_url", ""),
            })

        return formatted_items
    except Exception as e:
        logger.error("Failed to fetch clothing items from pipeline: %s", e)
        return []

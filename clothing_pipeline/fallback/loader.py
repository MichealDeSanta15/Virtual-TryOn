"""
Fallback dataset — provides a bundled set of demo clothing items
when live scraping fails or returns no results.

Uses a JSON manifest + local placeholder images so the try-on engine
always has something to work with, even offline.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from clothing_pipeline.config import FALLBACK_DIR
from clothing_pipeline.database.models import Product

logger = logging.getLogger(__name__)

# ── Bundled Demo Data ────────────────────────────────────────────────────
# A small hardcoded dataset inspired by DeepFashion2 categories.
# In production, replace this with actual images from the dataset.

DEMO_PRODUCTS = [
    {
        "title": "Classic White Formal Shirt",
        "brand": "Van Heusen",
        "price": 1499.0,
        "category": "shirt",
        "color": "white",
        "occasion": "formal",
        "sizes": ["S", "M", "L", "XL"],
    },
    {
        "title": "Navy Blue Slim Fit Blazer",
        "brand": "Raymond",
        "price": 4999.0,
        "category": "blazer",
        "color": "navy blue",
        "occasion": "wedding",
        "sizes": ["38", "40", "42", "44"],
    },
    {
        "title": "Embroidered Silk Kurta Set",
        "brand": "Manyavar",
        "price": 3599.0,
        "category": "kurta",
        "color": "maroon",
        "occasion": "festival",
        "sizes": ["S", "M", "L", "XL", "XXL"],
    },
    {
        "title": "Floral Print Anarkali Dress",
        "brand": "W",
        "price": 2299.0,
        "category": "anarkali",
        "color": "red",
        "occasion": "festival",
        "sizes": ["S", "M", "L", "XL"],
    },
    {
        "title": "Black Cocktail Dress",
        "brand": "Zara",
        "price": 3499.0,
        "category": "dress",
        "color": "black",
        "occasion": "party",
        "sizes": ["XS", "S", "M", "L"],
    },
    {
        "title": "Men's Grey Formal Trousers",
        "brand": "Arrow",
        "price": 1799.0,
        "category": "trousers",
        "color": "grey",
        "occasion": "formal",
        "sizes": ["30", "32", "34", "36"],
    },
    {
        "title": "Banarasi Silk Saree",
        "brand": "Sabyasachi",
        "price": 8999.0,
        "category": "saree",
        "color": "gold",
        "occasion": "wedding",
        "sizes": ["Free Size"],
    },
    {
        "title": "Casual Denim Jacket",
        "brand": "Levi's",
        "price": 2999.0,
        "category": "jacket",
        "color": "blue",
        "occasion": "casual",
        "sizes": ["S", "M", "L", "XL"],
    },
    {
        "title": "Printed Cotton T-Shirt",
        "brand": "H&M",
        "price": 599.0,
        "category": "t-shirt",
        "color": "multi",
        "occasion": "casual",
        "sizes": ["S", "M", "L", "XL"],
    },
    {
        "title": "Designer Lehenga Choli",
        "brand": "Kalki",
        "price": 12999.0,
        "category": "lehenga",
        "color": "pink",
        "occasion": "wedding",
        "sizes": ["S", "M", "L"],
    },
    {
        "title": "Slim Fit Chinos",
        "brand": "Allen Solly",
        "price": 1299.0,
        "category": "chinos",
        "color": "khaki",
        "occasion": "casual",
        "sizes": ["30", "32", "34", "36"],
    },
    {
        "title": "Party Wear Sequin Top",
        "brand": "Forever 21",
        "price": 1199.0,
        "category": "top",
        "color": "silver",
        "occasion": "party",
        "sizes": ["XS", "S", "M", "L"],
    },
    {
        "title": "Ethnic Sherwani Set",
        "brand": "Manyavar",
        "price": 7999.0,
        "category": "sherwani",
        "color": "ivory",
        "occasion": "wedding",
        "sizes": ["38", "40", "42", "44"],
    },
    {
        "title": "Joggers Track Pants",
        "brand": "Nike",
        "price": 2499.0,
        "category": "joggers",
        "color": "black",
        "occasion": "sports",
        "sizes": ["S", "M", "L", "XL"],
    },
    {
        "title": "Cotton Palazzo Pants",
        "brand": "Global Desi",
        "price": 899.0,
        "category": "palazzo",
        "color": "green",
        "occasion": "casual",
        "sizes": ["S", "M", "L", "XL"],
    },
    {
        "title": "Smart Casual Polo T-Shirt",
        "brand": "U.S. Polo",
        "price": 999.0,
        "category": "t-shirt",
        "color": "red",
        "occasion": "date",
        "sizes": ["S", "M", "L", "XL"],
    },
    {
        "title": "High-Waist Skinny Jeans",
        "brand": "Levi's",
        "price": 2199.0,
        "category": "jeans",
        "color": "dark blue",
        "occasion": "casual",
        "sizes": ["26", "28", "30", "32"],
    },
    {
        "title": "Linen Beach Shirt",
        "brand": "Marks & Spencer",
        "price": 1799.0,
        "category": "shirt",
        "color": "sky blue",
        "occasion": "beach",
        "sizes": ["S", "M", "L", "XL"],
    },
    {
        "title": "Zip-Up Hoodie",
        "brand": "Puma",
        "price": 2799.0,
        "category": "hoodie",
        "color": "grey",
        "occasion": "casual",
        "sizes": ["S", "M", "L", "XL"],
    },
    {
        "title": "Georgette Dupatta",
        "brand": "Fabindia",
        "price": 699.0,
        "category": "dupatta",
        "color": "peach",
        "occasion": "festival",
        "sizes": ["Free Size"],
    },
]


class FallbackDataset:
    """
    Provides fallback clothing data when live scraping is unavailable.

    Can filter by occasion, price range, and category just like the
    main search engine.
    """

    def __init__(self):
        self._products = self._load_products()
        self._generate_placeholder_images()

    def _load_products(self) -> List[Product]:
        """Load the bundled demo product data."""
        # First try loading from a JSON file
        manifest = FALLBACK_DIR / "manifest.json"
        if manifest.exists():
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    items = json.load(f)
                logger.info(
                    "Loaded %d items from fallback manifest", len(items)
                )
                return [
                    Product(
                        id=i + 10000,  # offset IDs to avoid DB conflicts
                        source="fallback",
                        source_url=f"fallback://{i}",
                        **item,
                    )
                    for i, item in enumerate(items)
                ]
            except Exception as e:
                logger.warning("Failed to load fallback manifest: %s", e)

        # Use hardcoded demo data
        logger.info("Using hardcoded fallback dataset (%d items)", len(DEMO_PRODUCTS))
        return [
            Product(
                id=i + 10000,
                source="fallback",
                source_url=f"fallback://{i}",
                **item,
            )
            for i, item in enumerate(DEMO_PRODUCTS)
        ]

    def _generate_placeholder_images(self):
        """
        Generate simple placeholder images for fallback products.
        Creates a colored rectangle with the product name.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            logger.warning("Pillow not installed — skipping placeholder images")
            return

        img_dir = FALLBACK_DIR / "images"
        img_dir.mkdir(parents=True, exist_ok=True)

        # Color map for categories
        color_map = {
            "shirt": "#4A90D9",
            "blazer": "#2C3E50",
            "kurta": "#C0392B",
            "anarkali": "#E74C3C",
            "dress": "#8E44AD",
            "trousers": "#7F8C8D",
            "saree": "#D4AC0D",
            "jacket": "#2980B9",
            "t-shirt": "#27AE60",
            "lehenga": "#E91E63",
            "chinos": "#795548",
            "top": "#FF5722",
            "sherwani": "#F39C12",
            "joggers": "#1ABC9C",
            "palazzo": "#00BCD4",
            "jeans": "#3F51B5",
            "hoodie": "#607D8B",
            "dupatta": "#FF9800",
        }

        for product in self._products:
            filename = f"fallback_{product.id}.png"
            filepath = img_dir / filename

            if filepath.exists():
                product.image_path = str(filepath)
                continue

            try:
                bg_color = color_map.get(product.category or "", "#95A5A6")
                img = Image.new("RGB", (400, 500), bg_color)
                draw = ImageDraw.Draw(img)

                # Draw product info as text
                try:
                    font = ImageFont.truetype("arial.ttf", 18)
                    font_small = ImageFont.truetype("arial.ttf", 14)
                except OSError:
                    font = ImageFont.load_default()
                    font_small = font

                # Title
                title = product.title or "Unknown"
                # Simple word wrap
                words = title.split()
                lines = []
                current = ""
                for w in words:
                    if len(current + " " + w) > 25:
                        lines.append(current)
                        current = w
                    else:
                        current = (current + " " + w).strip()
                if current:
                    lines.append(current)

                y = 180
                for line in lines:
                    draw.text((20, y), line, fill="white", font=font)
                    y += 24

                # Brand
                if product.brand:
                    draw.text(
                        (20, y + 10),
                        product.brand,
                        fill="#DDDDDD",
                        font=font_small,
                    )

                # Price
                if product.price:
                    draw.text(
                        (20, y + 35),
                        f"₹{product.price:,.0f}",
                        fill="#FFD700",
                        font=font,
                    )

                # Category badge
                if product.category:
                    draw.rounded_rectangle(
                        [(20, 20), (20 + len(product.category) * 10 + 20, 45)],
                        radius=5,
                        fill="#00000080",
                    )
                    draw.text(
                        (30, 24),
                        product.category.upper(),
                        fill="white",
                        font=font_small,
                    )

                # "DEMO" watermark
                draw.text(
                    (280, 460),
                    "DEMO",
                    fill="#FFFFFF40",
                    font=font,
                )

                img.save(str(filepath))
                product.image_path = str(filepath)

            except Exception as e:
                logger.debug(
                    "Failed to generate placeholder for %s: %s",
                    product.title,
                    e,
                )

    def get_all(self) -> List[Product]:
        """Return all fallback products."""
        return self._products.copy()

    def search(
        self,
        occasion: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        category: Optional[str] = None,
        color: Optional[str] = None,
        limit: int = 50,
    ) -> List[Product]:
        """Filter fallback products by criteria."""
        results = self._products

        if occasion:
            occ_lower = occasion.lower()
            results = [
                p for p in results
                if p.occasion and occ_lower in p.occasion.lower()
            ]

        if min_price is not None:
            results = [
                p for p in results
                if p.price is not None and p.price >= min_price
            ]

        if max_price is not None:
            results = [
                p for p in results
                if p.price is not None and p.price <= max_price
            ]

        if category:
            cat_lower = category.lower()
            results = [
                p for p in results
                if p.category and cat_lower in p.category.lower()
            ]

        if color:
            color_lower = color.lower()
            results = [
                p for p in results
                if p.color and color_lower in p.color.lower()
            ]

        return results[:limit]

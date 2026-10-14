"""
Configuration constants for the clothing pipeline.
"""

import os
from pathlib import Path

# Paths are configurable and created lazily, not at import time.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("EDGEAI_CATALOG_DATA", str(Path(os.getenv("EDGEAI_DATA", str(BASE_DIR / "data"))) / "catalog")))
IMAGE_DIR = DATA_DIR / "images"
DB_PATH = DATA_DIR / "products.db"
FALLBACK_DIR = DATA_DIR / "local"
RATE_LIMIT_DELAY = 1.0
REQUEST_TIMEOUT = 20_000
MAX_RETRIES = 2
RETRY_BACKOFF = 2.0
MAX_PAGES_PER_SOURCE = 1
MAX_ITEMS_PER_SOURCE = 12
VIEWPORT = {"width": 1366, "height": 768}
USER_AGENT = "EdgeAIResearchCatalog/1.0"
CACHE_MAX_ENTRIES = 500
CACHE_TTL_HOURS = 24
DB_JOURNAL_MODE = "WAL"
MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_CATALOG_BYTES = 512 * 1024 * 1024

# ── Occasion Mapping ─────────────────────────────────────────────────────────
# Maps event keywords → search terms and occasion tags
OCCASION_MAP = {
    "wedding": {
        "keywords": ["wedding outfit", "sherwani", "lehenga", "blazer formal",
                      "saree party wear", "wedding dress"],
        "occasion_tag": "wedding",
        "categories": ["blazer", "sherwani", "lehenga", "saree", "dress",
                        "suit", "kurta"],
    },
    "party": {
        "keywords": ["party wear", "club outfit", "party dress",
                      "sequin top", "cocktail dress"],
        "occasion_tag": "party",
        "categories": ["dress", "top", "shirt", "skirt", "jeans"],
    },
    "interview": {
        "keywords": ["formal wear", "office wear", "blazer", "formal shirt",
                      "formal trousers"],
        "occasion_tag": "formal",
        "categories": ["blazer", "shirt", "trousers", "suit"],
    },
    "casual": {
        "keywords": ["casual wear", "t-shirt", "jeans", "sneakers",
                      "casual dress"],
        "occasion_tag": "casual",
        "categories": ["t-shirt", "jeans", "shorts", "dress", "hoodie"],
    },
    "date": {
        "keywords": ["date night outfit", "smart casual", "stylish shirt",
                      "dress elegant"],
        "occasion_tag": "date",
        "categories": ["shirt", "dress", "blazer", "top", "jeans"],
    },
    "festival": {
        "keywords": ["ethnic wear", "kurta", "saree", "anarkali",
                      "festival dress"],
        "occasion_tag": "festival",
        "categories": ["kurta", "saree", "anarkali", "lehenga", "dupatta"],
    },
    "gym": {
        "keywords": ["gym wear", "track pants", "sports t-shirt",
                      "workout clothes"],
        "occasion_tag": "sports",
        "categories": ["t-shirt", "track pants", "shorts", "sports bra",
                        "hoodie"],
    },
    "beach": {
        "keywords": ["beachwear", "swimwear", "resort wear", "floral shirt"],
        "occasion_tag": "beach",
        "categories": ["shorts", "shirt", "swimwear", "dress", "sandals"],
    },
}

# Default fallback if event keyword is not recognized
DEFAULT_OCCASION = {
    "keywords": [],
    "occasion_tag": "general",
    "categories": [],
}

# ── Source URLs ───────────────────────────────────────────────────────────────
SOURCES = {
    "myntra": {
        "base_url": "https://www.myntra.com",
        "search_url": "https://www.myntra.com/{query}",
        "robots_url": "https://www.myntra.com/robots.txt",
    },
    "ajio": {
        "base_url": "https://www.ajio.com",
        "search_url": "https://www.ajio.com/search/?text={query}",
        "robots_url": "https://www.ajio.com/robots.txt",
    },
    "amazon": {
        "base_url": "https://www.amazon.in",
        "search_url": "https://www.amazon.in/s?k={query}",
        "robots_url": "https://www.amazon.in/robots.txt",
    },
}

OCCASION_MAP["freshers"] = {"keywords": ["party wear"], "occasion_tag": "party", "categories": ["dress", "shirt", "top", "blazer", "trousers"]}

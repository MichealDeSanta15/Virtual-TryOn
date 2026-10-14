"""
Configuration constants for the clothing pipeline.
"""

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
IMAGE_DIR = DATA_DIR / "images"
DB_PATH = DATA_DIR / "products.db"
FALLBACK_DIR = Path(__file__).resolve().parent / "fallback" / "dataset"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
FALLBACK_DIR.mkdir(parents=True, exist_ok=True)

# ── Scraper Settings ─────────────────────────────────────────────────────────
RATE_LIMIT_DELAY = 1.0          # seconds between requests (≈1 req/s)
REQUEST_TIMEOUT = 30_000        # milliseconds for Playwright navigation
MAX_RETRIES = 3                 # retries per failed request
RETRY_BACKOFF = 2.0             # exponential backoff multiplier

# Maximum number of product pages to scrape per source per query
MAX_PAGES_PER_SOURCE = 3
MAX_ITEMS_PER_SOURCE = 30

# ── Browser / Stealth ────────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

VIEWPORT = {"width": 1366, "height": 768}

# ── Cache Settings ────────────────────────────────────────────────────────────
CACHE_MAX_ENTRIES = 500         # LRU eviction threshold
CACHE_TTL_HOURS = 24            # time-to-live for cache entries

# ── Database ──────────────────────────────────────────────────────────────────
DB_JOURNAL_MODE = "WAL"         # write-ahead logging for concurrency

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

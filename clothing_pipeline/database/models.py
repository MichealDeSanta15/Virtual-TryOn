"""
Data models for the clothing pipeline.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List
import json


@dataclass
class Product:
    """Represents a clothing product scraped from an online store."""

    id: Optional[int] = None
    source: str = ""                # 'myntra', 'ajio', 'amazon'
    source_url: str = ""
    title: str = ""
    brand: Optional[str] = None
    price: Optional[float] = None
    currency: str = "INR"
    category: Optional[str] = None  # 'shirt', 'dress', 'jeans', etc.
    color: Optional[str] = None
    occasion: Optional[str] = None  # derived from event keyword
    sizes: Optional[List[str]] = None
    image_path: Optional[str] = None    # local file path
    image_url: Optional[str] = None     # remote URL
    metadata: Optional[dict] = None     # extra JSON data
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to a plain dictionary for API responses."""
        d = asdict(self)
        # Serialize datetimes to ISO strings
        for key in ("created_at", "updated_at"):
            if d[key] is not None:
                d[key] = d[key].isoformat()
        return d

    def to_db_row(self) -> dict:
        """Convert to a dict suitable for SQLite insertion."""
        return {
            "source": self.source,
            "source_url": self.source_url,
            "title": self.title,
            "brand": self.brand,
            "price": self.price,
            "currency": self.currency,
            "category": self.category,
            "color": self.color,
            "occasion": self.occasion,
            "sizes": json.dumps(self.sizes) if self.sizes else None,
            "image_path": self.image_path,
            "image_url": self.image_url,
            "metadata": json.dumps(self.metadata) if self.metadata else None,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "Product":
        """Construct a Product from a SQLite row dict."""
        sizes = None
        if row.get("sizes"):
            try:
                sizes = json.loads(row["sizes"])
            except (json.JSONDecodeError, TypeError):
                sizes = None

        metadata = None
        if row.get("metadata"):
            try:
                metadata = json.loads(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                metadata = None

        created_at = None
        if row.get("created_at"):
            try:
                created_at = datetime.fromisoformat(row["created_at"])
            except (ValueError, TypeError):
                pass

        updated_at = None
        if row.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(row["updated_at"])
            except (ValueError, TypeError):
                pass

        return cls(
            id=row.get("id"),
            source=row.get("source", ""),
            source_url=row.get("source_url", ""),
            title=row.get("title", ""),
            brand=row.get("brand"),
            price=row.get("price"),
            currency=row.get("currency", "INR"),
            category=row.get("category"),
            color=row.get("color"),
            occasion=row.get("occasion"),
            sizes=sizes,
            image_path=row.get("image_path"),
            image_url=row.get("image_url"),
            metadata=metadata,
            created_at=created_at,
            updated_at=updated_at,
        )


@dataclass
class ScrapeLog:
    """Log entry for a scraping operation."""

    id: Optional[int] = None
    query: str = ""
    source: str = ""
    status: str = ""            # 'success', 'error', 'timeout'
    items_found: int = 0
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class CacheEntry:
    """An entry in the LRU query cache."""

    id: Optional[int] = None
    cache_key: str = ""
    result_ids: List[int] = field(default_factory=list)
    hit_count: int = 0
    last_accessed: Optional[datetime] = None
    created_at: Optional[datetime] = None

    def to_db_row(self) -> dict:
        return {
            "cache_key": self.cache_key,
            "result_ids": json.dumps(self.result_ids),
            "hit_count": self.hit_count,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "CacheEntry":
        result_ids = []
        if row.get("result_ids"):
            try:
                result_ids = json.loads(row["result_ids"])
            except (json.JSONDecodeError, TypeError):
                pass

        last_accessed = None
        if row.get("last_accessed"):
            try:
                last_accessed = datetime.fromisoformat(row["last_accessed"])
            except (ValueError, TypeError):
                pass

        created_at = None
        if row.get("created_at"):
            try:
                created_at = datetime.fromisoformat(row["created_at"])
            except (ValueError, TypeError):
                pass

        return cls(
            id=row.get("id"),
            cache_key=row.get("cache_key", ""),
            result_ids=result_ids,
            hit_count=row.get("hit_count", 0),
            last_accessed=last_accessed,
            created_at=created_at,
        )

"""
Scraper orchestrator — coordinates all site-specific scrapers.
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict

from clothing_pipeline.database.models import Product, ScrapeLog
from clothing_pipeline.database.operations import ProductDB
from clothing_pipeline.scraper.base import BaseScraper
from clothing_pipeline.scraper.myntra import MyntraScraper
from clothing_pipeline.scraper.ajio import AjioScraper
from clothing_pipeline.scraper.amazon import AmazonScraper

logger = logging.getLogger(__name__)

__all__ = ["ScraperOrchestrator", "MyntraScraper", "AjioScraper", "AmazonScraper"]


class ScraperOrchestrator:
    """
    Coordinates scraping across Myntra, Ajio, and Amazon India.

    Runs scrapers concurrently (one browser per source), merges results,
    saves to database, and logs each operation.
    """

    def __init__(
        self,
        db: Optional[ProductDB] = None,
        sources: Optional[List[str]] = None,
    ):
        self.db = db or ProductDB()
        self.enabled_sources = sources or ["myntra", "ajio", "amazon"]
        self._scrapers: Dict[str, BaseScraper] = {}

    def _create_scrapers(self) -> Dict[str, BaseScraper]:
        """Instantiate enabled scrapers."""
        scrapers = {}
        if "myntra" in self.enabled_sources:
            scrapers["myntra"] = MyntraScraper()
        if "ajio" in self.enabled_sources:
            scrapers["ajio"] = AjioScraper()
        if "amazon" in self.enabled_sources:
            scrapers["amazon"] = AmazonScraper()
        return scrapers

    async def scrape_all(self, query: str) -> List[Product]:
        """
        Scrape all enabled sources for the given query.

        Each source runs in its own browser instance concurrently.
        Results are merged, deduplicated, and saved to the database.

        Returns:
            Combined list of products from all sources.
        """
        scrapers = self._create_scrapers()
        all_products: List[Product] = []

        # Start all browsers
        for scraper in scrapers.values():
            await scraper.start()

        try:
            # Run scrapers concurrently
            tasks = {
                name: asyncio.create_task(
                    self._scrape_with_logging(scraper, query)
                )
                for name, scraper in scrapers.items()
            }

            results = await asyncio.gather(
                *tasks.values(), return_exceptions=True
            )

            for name, result in zip(tasks.keys(), results):
                if isinstance(result, Exception):
                    logger.error(
                        "[orchestrator] %s scraper failed: %s",
                        name,
                        str(result),
                    )
                elif isinstance(result, list):
                    all_products.extend(result)

        finally:
            # Stop all browsers
            for scraper in scrapers.values():
                try:
                    await scraper.stop()
                except Exception as e:
                    logger.warning("Error stopping scraper: %s", str(e))

        # Save to database
        if all_products:
            ids = self.db.bulk_insert(all_products)
            logger.info(
                "[orchestrator] Saved %d products to database", len(ids)
            )
            # Update product IDs from DB
            for product, pid in zip(all_products, ids):
                product.id = pid

        logger.info(
            "[orchestrator] Total products scraped: %d", len(all_products)
        )
        return all_products

    async def _scrape_with_logging(
        self, scraper: BaseScraper, query: str
    ) -> List[Product]:
        """Scrape a single source with timing and logging."""
        start = time.monotonic()
        status = "success"
        error_msg = None
        products = []

        try:
            products = await scraper.scrape(query)
        except Exception as e:
            status = "error"
            error_msg = str(e)
            logger.error(
                "[%s] Scraper error: %s",
                scraper.source_name,
                error_msg,
                exc_info=True,
            )

        duration_ms = int((time.monotonic() - start) * 1000)

        # Log the operation
        log = ScrapeLog(
            query=query,
            source=scraper.source_name,
            status=status,
            items_found=len(products),
            error_message=error_msg,
            duration_ms=duration_ms,
        )
        self.db.log_scrape(log)

        logger.info(
            "[%s] Scraped %d items in %dms (status: %s)",
            scraper.source_name,
            len(products),
            duration_ms,
            status,
        )
        return products

    async def scrape_source(
        self, source: str, query: str
    ) -> List[Product]:
        """Scrape a single source only."""
        scrapers = self._create_scrapers()
        scraper = scrapers.get(source)
        if not scraper:
            logger.error("Unknown source: %s", source)
            return []

        await scraper.start()
        try:
            products = await self._scrape_with_logging(scraper, query)
            if products:
                ids = self.db.bulk_insert(products)
                for product, pid in zip(products, ids):
                    product.id = pid
            return products
        finally:
            await scraper.stop()

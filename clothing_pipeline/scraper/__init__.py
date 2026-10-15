"""Bounded scraping with isolated source failures and explicit per-source status."""
import asyncio
from pathlib import Path
from clothing_pipeline.config import IMAGE_DIR
from clothing_pipeline.database.models import ScrapeLog
from clothing_pipeline.database.operations import ProductDB
from .sources import DEFAULT_SOURCES, LIVE_SOURCES, FEED_STORES


class ScraperOrchestrator:
    def __init__(self, db=None, sources=None, image_dir=None, filters=None):
        self.db = db or ProductDB()
        self.sources = list(DEFAULT_SOURCES if sources is None else sources)
        if set(self.sources)-set(LIVE_SOURCES): raise ValueError('Unsupported retailer')
        self.filters = filters or {}
        self.image_dir = Path(image_dir or IMAGE_DIR)
        self.last_status = []

    async def scrape_all(self, query):
        from .myntra import MyntraScraper
        from .ajio import AjioScraper
        from .amazon import AmazonScraper
        from .network import SafeTransport
        from .shopify import PublicFeedScraper, now_utc
        classes = {'myntra':MyntraScraper,'ajio':AjioScraper,'amazon':AmazonScraper}
        async with SafeTransport(self.image_dir) as transport:
            scrapers = [PublicFeedScraper(name, transport, self.filters) if name in FEED_STORES
                        else classes[name](transport) for name in self.sources]
            async def run(scraper):
                try:
                    return await asyncio.wait_for(scraper.scrape(query), timeout=100)
                except asyncio.TimeoutError:
                    scraper.status.update(status='timeout',message='Source exceeded 100 second deadline; retaining only completed fresh photos')
                    return getattr(scraper, 'products', [])
                except Exception as exc:
                    scraper.status.update(status='error', message=f'{type(exc).__name__}: {exc}'[:1000])
                    return []
                finally:
                    scraper.status['completed_at'] = now_utc()
            groups = await asyncio.gather(*(run(s) for s in scrapers), return_exceptions=True)
            self.last_status = [s.status for s in scrapers]
            products = [p for group in groups if isinstance(group,list) for p in group]
            for product in products:
                product.metadata = {**(product.metadata or {})}
                product.metadata.setdefault('observed_at', now_utc())
        for status in self.last_status:
            self.db.log_scrape(ScrapeLog(query=query,source=status['source'],status=status['status'],
                items_found=status['usable'],error_message=status['message']))
        if products:
            ids = self.db.bulk_insert(products)
            for product,pid in zip(products,ids): product.id = pid
            self.db.clear_cache()
        return products

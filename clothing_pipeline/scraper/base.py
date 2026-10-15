"""Shared browser lifecycle and image pipeline. No stealth/CAPTCHA circumvention."""
import asyncio
import logging
import time
from abc import ABC, abstractmethod
from urllib.parse import urlsplit
from clothing_pipeline.config import REQUEST_TIMEOUT, MAX_ITEMS_PER_SOURCE, VIEWPORT, USER_AGENT
from clothing_pipeline.validation import clean_price, infer_category
from .network import allowed_url, RateLimiter

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    def __init__(self, transport):
        self.transport = transport
        self._playwright = self._browser = self._context = None
        self.status = {'source':self.source_name, 'status':'starting','message':'','found':0,'usable':0}

    @property
    @abstractmethod
    def source_name(self): ...
    @abstractmethod
    def build_search_url(self, query): ...
    @abstractmethod
    async def parse_products(self, page, query): ...

    async def start(self):
        from playwright.async_api import async_playwright
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context(viewport=VIEWPORT, locale='en-IN',
            timezone_id='Asia/Kolkata', user_agent=USER_AGENT, accept_downloads=False,
            service_workers='block')
        async def route_request(route):
            request = route.request
            # Don't download duplicate images/fonts/media in the browser. The
            # dedicated downloader checks size, content, redirects and robots.
            if request.resource_type in ('image','media','font') or not allowed_url(request.url):
                return await route.abort()
            if not await self.transport.robots.can_fetch(request.url):
                return await route.abort()
            await self.transport.limiter(request.url).wait()
            await route.continue_()
        await self._context.route('**/*', route_request)

    async def stop(self):
        for resource in (self._context,self._browser):
            if resource is not None:
                try: await asyncio.wait_for(resource.close(), timeout=5)
                except Exception: logger.debug('Browser cleanup failed',exc_info=True)
        if self._playwright is not None:
            try: await asyncio.wait_for(self._playwright.stop(), timeout=5)
            except Exception: logger.debug('Playwright cleanup failed',exc_info=True)
        self._context = self._browser = self._playwright = None

    async def scrape(self, query):
        url = self.build_search_url(query)
        try:
            if not await self.transport.robots.can_fetch(url):
                self.status.update(status='blocked', message=self.transport.robots.reason(url)+'; URL disallowed or unavailable')
                return []
            await self.start()
            page = await self._context.new_page()
            response = await page.goto(url,timeout=REQUEST_TIMEOUT,wait_until='domcontentloaded')
            if not response or response.status in (401,403,429):
                self.status.update(status='blocked',message=f'HTTP {response.status if response else "no response"}; stopped without bypass')
                return []
            if response.status >= 400: raise ValueError(f'HTTP {response.status}')
            body = (await page.locator('body').inner_text(timeout=5000)).casefold()
            if any(term in body for term in ('enter the characters you see','verify you are human','robot check','access denied')):
                self.status.update(status='blocked',message='Access challenge detected; no CAPTCHA bypass attempted')
                return []
            products = (await self.parse_products(page, query))[:MAX_ITEMS_PER_SOURCE]
            self.status['found'] = len(products)
            valid = []
            seen = set()
            failures = 0
            from clothing_pipeline.search.engine import SearchEngine
            info = SearchEngine.get_occasion_info(query)
            for product in products:
                if not product.title or not product.source_url or product.source_url in seen: continue
                if product.brand and product.title.casefold() == product.brand.casefold():
                    continue  # A brand-only heading is not a usable product title.
                if not allowed_url(product.source_url) or not product.image_url: continue
                # A successful card parse is not enough: require a usable downloaded photograph.
                try:
                    product.image_path = await self.transport.download_image(product.image_url)
                    product.category = infer_category(product.title, query)
                    if info['known']: product.occasion = info['occasion_tag']
                    product.metadata = {**(product.metadata or {}),'origin':'retailer','is_placeholder':False,
                                        'occasion_inferred':True,'image_validated':True}
                    seen.add(product.source_url);valid.append(product)
                except Exception as exc:
                    failures += 1
                    logger.info('%s image skipped: %s',self.source_name,exc)
            self.status.update(status='ok' if valid else 'empty',usable=len(valid),
                message=f'{len(valid)} validated product images; {failures} downloads rejected' if products else 'No product cards found; page/selectors may have changed')
            return valid
        except asyncio.CancelledError:
            self.status.update(status='timeout',message='Search deadline reached')
            raise
        except Exception as exc:
            self.status.update(status='error',message=f'{type(exc).__name__}: {exc}'[:1000])
            return []
        finally:
            await self.stop()

    clean_price = staticmethod(clean_price)
    @staticmethod
    def clean_text(text): return ' '.join((text or '').split())
    @staticmethod
    def _infer_category(query, title): return infer_category(title,query)

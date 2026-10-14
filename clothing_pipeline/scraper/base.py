"""
Base scraper with Playwright stealth mode, rate limiting, and image downloading.
"""

import asyncio
import logging
import random
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

import aiohttp
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from clothing_pipeline.config import (
    RATE_LIMIT_DELAY,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RETRY_BACKOFF,
    USER_AGENTS,
    VIEWPORT,
    IMAGE_DIR,
    MAX_ITEMS_PER_SOURCE,
)
from clothing_pipeline.database.models import Product
from clothing_pipeline.scraper.robots import RobotsChecker

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token-bucket rate limiter (≈1 request/second by default)."""

    def __init__(self, min_delay: float = RATE_LIMIT_DELAY):
        self.min_delay = min_delay
        self._last_request_time = 0.0

    async def wait(self):
        """Wait until it's safe to make the next request."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.min_delay:
            wait_time = self.min_delay - elapsed
            # Add small jitter to appear more human
            jitter = random.uniform(0.1, 0.5)
            await asyncio.sleep(wait_time + jitter)
        self._last_request_time = time.monotonic()


class BaseScraper(ABC):
    """
    Abstract base scraper using Playwright in stealth mode.

    Subclasses implement:
      - build_search_url(query) -> str
      - parse_products(page) -> List[Product]
      - source_name -> str
    """

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.robots_checker = RobotsChecker()
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._playwright = None

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the source identifier: 'myntra', 'ajio', or 'amazon'."""
        ...

    @abstractmethod
    def build_search_url(self, query: str) -> str:
        """Build the search URL for the given query."""
        ...

    @abstractmethod
    async def parse_products(self, page: Page, query: str) -> List[Product]:
        """
        Parse product cards from the current page.

        Returns a list of Product objects with at least:
        title, price, image_url, source_url, brand, category.
        """
        ...

    # ── Browser lifecycle ────────────────────────────────────────────────

    async def start(self):
        """Launch a stealth browser instance."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        user_agent = random.choice(USER_AGENTS)
        self._context = await self._browser.new_context(
            user_agent=user_agent,
            viewport=VIEWPORT,
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            # Stealth: mask webdriver flag
            java_script_enabled=True,
        )
        # Inject stealth scripts to mask automation
        await self._context.add_init_script("""
            // Overwrite navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            // Overwrite chrome runtime
            window.chrome = {
                runtime: {},
            };

            // Overwrite permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) =>
                parameters.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(parameters);

            // Overwrite plugins length
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });

            // Overwrite languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'hi'],
            });
        """)

        logger.info(
            "Started stealth browser for %s (UA: %s)",
            self.source_name,
            user_agent[:50],
        )

    async def stop(self):
        """Close the browser and cleanup."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Stopped browser for %s", self.source_name)

    # ── Navigation ───────────────────────────────────────────────────────

    async def navigate(self, page: Page, url: str) -> bool:
        """
        Navigate to a URL with rate limiting, retries, and robots.txt check.

        Returns True if navigation succeeded.
        """
        # Check robots.txt
        if not self.robots_checker.can_fetch(url):
            logger.warning(
                "[%s] Blocked by robots.txt: %s", self.source_name, url
            )
            return False

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                await self.rate_limiter.wait()
                response = await page.goto(
                    url,
                    timeout=REQUEST_TIMEOUT,
                    wait_until="domcontentloaded",
                )
                if response and response.ok:
                    # Wait a bit for dynamic content
                    await page.wait_for_timeout(random.randint(1000, 2500))
                    return True
                else:
                    status = response.status if response else "no response"
                    logger.warning(
                        "[%s] HTTP %s for %s (attempt %d/%d)",
                        self.source_name,
                        status,
                        url,
                        attempt,
                        MAX_RETRIES,
                    )
            except Exception as e:
                logger.warning(
                    "[%s] Navigation error for %s (attempt %d/%d): %s",
                    self.source_name,
                    url,
                    attempt,
                    MAX_RETRIES,
                    str(e),
                )

            if attempt < MAX_RETRIES:
                backoff = RETRY_BACKOFF ** attempt + random.uniform(0.5, 1.5)
                await asyncio.sleep(backoff)

        logger.error(
            "[%s] Failed to load %s after %d attempts",
            self.source_name,
            url,
            MAX_RETRIES,
        )
        return False

    # ── Scraping ─────────────────────────────────────────────────────────

    async def scrape(self, query: str) -> List[Product]:
        """
        Main scraping entry point.

        1. Build search URL
        2. Navigate with stealth
        3. Parse product cards
        4. Download images
        5. Return products with local image paths
        """
        url = self.build_search_url(query)
        logger.info("[%s] Scraping: %s", self.source_name, url)

        page = await self._context.new_page()
        try:
            success = await self.navigate(page, url)
            if not success:
                return []

            products = await self.parse_products(page, query)
            products = products[:MAX_ITEMS_PER_SOURCE]

            logger.info(
                "[%s] Found %d products for '%s'",
                self.source_name,
                len(products),
                query,
            )

            # Download images in parallel
            if products:
                await self._download_images(products)

            return products
        except Exception as e:
            logger.error(
                "[%s] Scraping failed for '%s': %s",
                self.source_name,
                query,
                str(e),
                exc_info=True,
            )
            return []
        finally:
            await page.close()

    # ── Image Download ───────────────────────────────────────────────────

    async def _download_images(self, products: List[Product]):
        """Download product images concurrently (max 5 at a time)."""
        source_dir = IMAGE_DIR / self.source_name
        source_dir.mkdir(parents=True, exist_ok=True)

        semaphore = asyncio.Semaphore(5)

        async def download_one(product: Product):
            if not product.image_url:
                return
            async with semaphore:
                try:
                    ext = ".jpg"
                    filename = f"{uuid.uuid4().hex}{ext}"
                    filepath = source_dir / filename

                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            product.image_url,
                            timeout=aiohttp.ClientTimeout(total=15),
                            headers={"User-Agent": random.choice(USER_AGENTS)},
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.read()
                                filepath.write_bytes(data)
                                product.image_path = str(filepath)
                                logger.debug(
                                    "Downloaded image: %s", filepath.name
                                )
                            else:
                                logger.warning(
                                    "Image download HTTP %d: %s",
                                    resp.status,
                                    product.image_url[:80],
                                )
                except Exception as e:
                    logger.warning(
                        "Image download failed: %s — %s",
                        product.image_url[:80],
                        str(e),
                    )

        tasks = [download_one(p) for p in products]
        await asyncio.gather(*tasks, return_exceptions=True)

        downloaded = sum(1 for p in products if p.image_path)
        logger.info(
            "[%s] Downloaded %d/%d images",
            self.source_name,
            downloaded,
            len(products),
        )

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def clean_price(text: str) -> Optional[float]:
        """Extract numeric price from text like '₹1,299' or 'Rs. 2,499'."""
        if not text:
            return None
        import re
        # Remove currency symbols, commas, spaces
        cleaned = re.sub(r"[₹,Rs.\s]", "", text)
        # Find the first number (possibly with decimal)
        match = re.search(r"(\d+\.?\d*)", cleaned)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    @staticmethod
    def clean_text(text: str) -> str:
        """Strip and normalize whitespace in text."""
        if not text:
            return ""
        return " ".join(text.strip().split())

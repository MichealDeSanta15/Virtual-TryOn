"""
Myntra scraper — extracts product cards from Myntra search results.
"""

import logging
import re
from typing import List
from urllib.parse import quote_plus, quote, urljoin

from playwright.async_api import Page

from clothing_pipeline.database.models import Product
from clothing_pipeline.scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class MyntraScraper(BaseScraper):
    """Scraper for www.myntra.com"""

    @property
    def source_name(self) -> str:
        return "myntra"

    def build_search_url(self, query: str) -> str:
        # Myntra uses slug-style URLs: /query-text
        slug = quote(query.lower().strip().replace(" ", "-"), safe="-")
        return f"https://www.myntra.com/{slug}"

    async def parse_products(self, page: Page, query: str) -> List[Product]:
        products = []

        try:
            # Wait for product grid to load
            await page.wait_for_selector(
                ".results-base, .search-searchProductsContainer, [class*='product-base']",
                timeout=10_000,
            )
        except Exception:
            logger.warning("[myntra] Product grid did not load for '%s'", query)
            # Try scrolling to trigger lazy load
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await page.wait_for_timeout(2000)

        # Extract product cards
        cards = await page.query_selector_all(
            "li.product-base, [class*='product-base']"
        )

        if not cards:
            logger.warning("[myntra] No product cards found for '%s'", query)
            return products

        for card in cards[:12]:
            try:
                product = Product(source="myntra")

                # Title / product name
                title_el = await card.query_selector(
                    ".product-product, [class*='product-product']"
                )
                if title_el:
                    product.title = self.clean_text(
                        await title_el.inner_text()
                    )

                # Brand
                brand_el = await card.query_selector(
                    ".product-brand, [class*='product-brand']"
                )
                if brand_el:
                    product.brand = self.clean_text(
                        await brand_el.inner_text()
                    )

                # If no title, use brand + product description
                if not product.title and product.brand:
                    product.title = product.brand

                if not product.title:
                    continue  # skip cards we can't identify

                # Price — try discounted price first, then original
                price_el = await card.query_selector(".product-discountedPrice")
                if price_el is None:
                    price_el = await card.query_selector(".product-price")
                if price_el:
                    product.price = self.clean_price(
                        await price_el.inner_text()
                    )

                # Image
                img_el = await card.query_selector(
                    "img.img-responsive, picture img, img[class*='img-responsive']"
                )
                if img_el:
                    src = await img_el.get_attribute("src")
                    if not src or src.startswith("data:"):
                        src = await img_el.get_attribute("data-src")
                    if src and not src.startswith("data:"):
                        src = urljoin("https://www.myntra.com", src)
                        # Upgrade to high-res
                        product.image_url = src.replace(
                            "/w_200,", "/w_720,"
                        ).replace("h_200", "h_720")

                # Product link
                link_el = await card.query_selector("a[href]")
                if link_el:
                    href = await link_el.get_attribute("href")
                    if href:
                        if href.startswith("/"):
                            href = f"https://www.myntra.com{href}"
                        product.source_url = urljoin("https://www.myntra.com", href)

                if not product.source_url:
                    href = await card.get_attribute("href")
                    if href:
                        product.source_url = urljoin("https://www.myntra.com", href)

                # Category — derive from query or title
                product.category = self._infer_category(
                    query, product.title or ""
                )

                # Occasion — from the search query context
                product.occasion = query.split()[0] if query else None

                products.append(product)

            except Exception as e:
                logger.debug(
                    "[myntra] Error parsing product card: %s", str(e)
                )
                continue

        logger.info("[myntra] Parsed %d products", len(products))
        return products


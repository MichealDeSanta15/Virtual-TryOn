"""
Amazon India scraper — extracts product cards from Amazon.in search results.
"""

import logging
from typing import List
from urllib.parse import quote_plus

from playwright.async_api import Page

from clothing_pipeline.database.models import Product
from clothing_pipeline.scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class AmazonScraper(BaseScraper):
    """Scraper for www.amazon.in"""

    @property
    def source_name(self) -> str:
        return "amazon"

    def build_search_url(self, query: str) -> str:
        encoded = quote_plus(query)
        return f"https://www.amazon.in/s?k={encoded}&i=apparel"

    async def parse_products(self, page: Page, query: str) -> List[Product]:
        products = []

        try:
            # Wait for search results
            await page.wait_for_selector(
                ".s-main-slot, .s-search-results, [data-component-type='s-search-result']",
                timeout=10_000,
            )
        except Exception:
            logger.warning("[amazon] Search results did not load for '%s'", query)
            await page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight / 2)"
            )
            await page.wait_for_timeout(2000)

        # Extract product cards
        cards = await page.query_selector_all(
            "[data-component-type='s-search-result']"
        )

        if not cards:
            # Fallback
            cards = await page.query_selector_all(
                ".s-result-item[data-asin]:not([data-asin=''])"
            )

        if not cards:
            logger.warning("[amazon] No product cards found for '%s'", query)
            return products

        for card in cards:
            try:
                # Skip sponsored / ad cards without product data
                asin = await card.get_attribute("data-asin")
                if not asin:
                    continue

                product = Product(source="amazon")

                # Title
                title_el = await card.query_selector(
                    "h2 a span, h2 span, .a-size-base-plus, .a-size-medium"
                )
                if title_el:
                    product.title = self.clean_text(
                        await title_el.inner_text()
                    )

                if not product.title:
                    continue

                # Brand — often embedded in the title or a separate span
                brand_el = await card.query_selector(
                    ".a-row .a-size-base:first-child, "
                    "[class*='brand'], .a-color-base:first-child"
                )
                if brand_el:
                    brand_text = self.clean_text(await brand_el.inner_text())
                    # Amazon sometimes puts brand as the first line
                    if brand_text and len(brand_text) < 50:
                        product.brand = brand_text

                # Price
                price_el = await card.query_selector(
                    ".a-price .a-offscreen, .a-price-whole, "
                    "[data-a-color='base'] .a-offscreen"
                )
                if price_el:
                    product.price = self.clean_price(
                        await price_el.inner_text()
                    )

                # Image
                img_el = await card.query_selector(
                    ".s-image, img[data-image-latency='s-product-image']"
                )
                if img_el:
                    src = await img_el.get_attribute("src")
                    if src:
                        # Upgrade thumbnail to larger image
                        # Amazon uses _AC_UL200_ style suffixes
                        product.image_url = src.replace(
                            "_AC_UL320_", "_AC_UL600_"
                        ).replace("_AC_UL200_", "_AC_UL600_")

                # Product link
                link_el = await card.query_selector(
                    "h2 a[href], a.a-link-normal[href*='/dp/']"
                )
                if link_el:
                    href = await link_el.get_attribute("href")
                    if href:
                        if href.startswith("/"):
                            href = f"https://www.amazon.in{href}"
                        product.source_url = href

                # Color — sometimes in a small text under the title
                color_el = await card.query_selector(
                    "[class*='color'], .a-color-base.a-text-normal"
                )
                if color_el:
                    color_text = self.clean_text(await color_el.inner_text())
                    if color_text and len(color_text) < 30:
                        product.color = color_text

                product.category = self._infer_category(
                    query, product.title or ""
                )
                product.occasion = query.split()[0] if query else None

                products.append(product)

            except Exception as e:
                logger.debug(
                    "[amazon] Error parsing product card: %s", str(e)
                )
                continue

        logger.info("[amazon] Parsed %d products", len(products))
        return products

    @staticmethod
    def _infer_category(query: str, title: str) -> str:
        combined = f"{query} {title}".lower()
        categories = [
            "shirt", "t-shirt", "jeans", "trousers", "dress", "saree",
            "kurta", "lehenga", "blazer", "jacket", "hoodie", "shorts",
            "skirt", "top", "sweater", "suit", "sherwani", "anarkali",
            "palazzo", "dupatta", "chinos", "joggers", "track pants",
        ]
        for cat in categories:
            if cat in combined:
                return cat
        return "clothing"

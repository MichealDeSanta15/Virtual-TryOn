"""
Ajio scraper — extracts product cards from Ajio search results.
"""

import logging
from typing import List
from urllib.parse import quote_plus

from playwright.async_api import Page

from clothing_pipeline.database.models import Product
from clothing_pipeline.scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class AjioScraper(BaseScraper):
    """Scraper for www.ajio.com"""

    @property
    def source_name(self) -> str:
        return "ajio"

    def build_search_url(self, query: str) -> str:
        encoded = quote_plus(query)
        return f"https://www.ajio.com/search/?text={encoded}"

    async def parse_products(self, page: Page, query: str) -> List[Product]:
        products = []

        try:
            # Wait for product listing
            await page.wait_for_selector(
                ".rilrtl-products-list, .item, [class*='product-list'], "
                "[class*='rilrtl-products']",
                timeout=10_000,
            )
        except Exception:
            logger.warning("[ajio] Product list did not load for '%s'", query)
            await page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight / 2)"
            )
            await page.wait_for_timeout(2000)

        # Extract product cards
        cards = await page.query_selector_all(
            ".item.rilrtl-products-list__item, "
            "[class*='rilrtl-products-list__item'], "
            ".rilrtl-products-list .item"
        )

        if not cards:
            # Fallback: try broader selectors
            cards = await page.query_selector_all(
                "[data-testid='product-item'], .product-card"
            )

        if not cards:
            logger.warning("[ajio] No product cards found for '%s'", query)
            return products

        for card in cards:
            try:
                product = Product(source="ajio")

                # Brand
                brand_el = await card.query_selector(
                    ".brand, [class*='brand'], .nameCls"
                )
                if brand_el:
                    product.brand = self.clean_text(
                        await brand_el.inner_text()
                    )

                # Title / product name
                name_el = await card.query_selector(
                    ".nameCls, [class*='name'], .product-name"
                )
                if name_el:
                    product.title = self.clean_text(
                        await name_el.inner_text()
                    )

                if not product.title:
                    product.title = product.brand or ""
                if not product.title:
                    continue

                # Price
                price_el = await card.query_selector(
                    ".price strong, [class*='price'] strong, "
                    ".rilrtl-products-list__item .price, .price"
                )
                if price_el:
                    product.price = self.clean_price(
                        await price_el.inner_text()
                    )

                # Image
                img_el = await card.query_selector(
                    "img.rilrtl-lazy-img, img[class*='lazy-img'], "
                    "img.imgC, picture img, img"
                )
                if img_el:
                    src = (
                        await img_el.get_attribute("src")
                        or await img_el.get_attribute("data-src")
                        or await img_el.get_attribute("data-lazy")
                    )
                    if src and not src.startswith("data:"):
                        if src.startswith("//"):
                            src = f"https:{src}"
                        product.image_url = src

                # Product link
                link_el = await card.query_selector("a[href]")
                if link_el:
                    href = await link_el.get_attribute("href")
                    if href:
                        if href.startswith("/"):
                            href = f"https://www.ajio.com{href}"
                        product.source_url = href

                # Color — sometimes shown in a chip or text
                color_el = await card.query_selector(
                    "[class*='color'], .shade"
                )
                if color_el:
                    product.color = self.clean_text(
                        await color_el.inner_text()
                    )

                product.category = self._infer_category(
                    query, product.title or ""
                )
                product.occasion = query.split()[0] if query else None

                products.append(product)

            except Exception as e:
                logger.debug(
                    "[ajio] Error parsing product card: %s", str(e)
                )
                continue

        logger.info("[ajio] Parsed %d products", len(products))
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

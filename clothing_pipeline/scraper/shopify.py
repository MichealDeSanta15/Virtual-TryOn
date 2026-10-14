"""Live public Shopify feeds, bounded discovery and variant-aware image selection.

No API key, browser, CAPTCHA solving or access-control bypass. Never substitutes
saved products on failure. robots.txt is checked for every destination.
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import re
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from clothing_pipeline.database.models import Product
from clothing_pipeline.search.engine import SearchEngine
from clothing_pipeline.validation import infer_category, tryon_category
from .network import allowed_url
from .sources import FEED_STORES

PAGE_SIZE = 100
MAX_PAGES = 3
MAX_IMAGES = 8
MAX_IMAGE_ATTEMPTS = 12


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def feed_price(value):
    """Feed prices are decimal major currency units, not Shopify .js cents."""
    if isinstance(value, bool) or not re.fullmatch(r'\d+(?:\.\d{1,2})?', str(value)):
        return None
    try:
        price = Decimal(str(value))
        return float(price) if price.is_finite() and 0 < price < 100_000_000 else None
    except (InvalidOperation, OverflowError):
        return None


def storefront_currency(html):
    match = re.search(r'Shopify\.currency\s*=\s*(\{[^;\n]+\})\s*;', html)
    if not match:
        raise ValueError('Storefront currency could not be verified; prices not assumed to be INR')
    currency = json.loads(match[1]).get('active')
    if currency != 'INR':
        raise ValueError(f'Storefront currency is {currency!r}, not INR; no currency conversion guessed')
    return currency


def image_url(src):
    if not isinstance(src, str):
        return None
    if src.startswith('//'):
        src = 'https:' + src
    if not allowed_url(src):
        return None
    # Request a sufficient but bounded product photo rather than a 6K original.
    p = urlsplit(src)
    params = [(k, v) for k, v in parse_qsl(p.query) if k != 'width']
    params.append(('width', '1024'))
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(params), ''))


def parse_product(raw, source, currency, observed_at, color=None):
    if not isinstance(raw, dict) or currency != 'INR':
        return None
    name, root = FEED_STORES[source]
    title = ' '.join(str(raw.get('title') or '').split())[:300]
    handle = raw.get('handle', '')
    if not title or not isinstance(handle, str) or not re.fullmatch(r'[a-zA-Z0-9_-]+', handle):
        return None
    kind = str(raw.get('product_type') or '')
    if re.search(r'\b(?:sets?|bundles?|looks?|co[ -]?ords?|kids?|children)\b', title+' '+kind, re.I):
        return None
    category = infer_category(title, kind)
    if category == 'clothing' and re.search(r'\btees?\b', kind, re.I):
        category = 't-shirt'
    if not tryon_category(category, title):
        return None
    options = raw.get('options') or []
    color_key = size_key = None
    for option in options:
        if not isinstance(option, dict) or option.get('position') not in (1, 2, 3):
            continue
        if str(option.get('name', '')).casefold() in ('color', 'colour'):
            color_key = f"option{option['position']}"
        if str(option.get('name', '')).casefold() == 'size':
            size_key = f"option{option['position']}"
    variants = []
    for v in raw.get('variants') or []:
        if not isinstance(v, dict) or v.get('available') is not True:
            continue
        price = feed_price(v.get('price'))
        if price is None:
            continue
        variant_color = str(v.get(color_key) or '') if color_key else ''
        if color and not re.search(r'\b'+re.escape(color)+r'\b', variant_color or title, re.I):
            continue
        variants.append((price, v))
    if not variants:
        return None
    price, variant = min(variants, key=lambda item: item[0])
    selected_color = str(variant.get(color_key) or '') if color_key else ''
    images = [im for im in (raw.get('images') or []) if isinstance(im, dict)]
    featured = variant.get('featured_image')
    if not isinstance(featured, dict):
        featured = next((im for im in images if variant.get('id') in (im.get('variant_ids') or [])), None)
    # With multiple colours, do not pretend an unrelated first photo depicts the
    # selected colour. Require a variant-associated image in that situation.
    all_colors = {str(v.get(color_key) or '') for v in raw.get('variants', []) if isinstance(v, dict)} if color_key else set()
    if featured is None and len(all_colors) > 1:
        return None
    featured = featured or next(iter(images), {})
    photo = image_url(featured.get('src'))
    if not photo:
        return None
    sizes = sorted({str(v.get(size_key)) for _, v in variants if size_key and v.get(size_key)
                    and (not color_key or str(v.get(color_key) or '') == selected_color)})
    # Stable product URL avoids producing a different database ID as the cheapest
    # available size changes. The exact observed variant is recorded in metadata.
    return Product(source=source, source_url=root+'/products/'+handle, title=title,
                   brand=str(raw.get('vendor') or name)[:100], price=price, currency=currency,
                   category=category, color=selected_color or None, sizes=sizes,
                   image_url=photo, metadata={'origin':'public_storefront_feed', 'is_placeholder':False,
                       'observed_at':observed_at, 'available_at_fetch':True,
                       'variant_id':variant.get('id'), 'variant_title':variant.get('title'),
                       'price_note':'Lowest observed available variant price matching the selected colour; verify size and final price at retailer.',
                       'retailer_updated_at':raw.get('updated_at')})


class PublicFeedScraper:
    def __init__(self, source, transport, filters=None):
        self.source_name = source
        self.transport = transport
        self.filters = filters or {}
        self.status = {'source':source, 'status':'starting', 'message':'', 'found':0, 'usable':0,
                       'scanned':0, 'pages':0, 'checked_at':None, 'coverage':'bounded public feed, not entire inventory'}
        self.products = []

    async def scrape(self, query):
        _, root = FEED_STORES[self.source_name]
        filters = dict(self.filters)
        filters.setdefault('event', query)
        max_images = min(MAX_IMAGES, filters.get('limit', MAX_IMAGES))
        requested_color = filters.get('color')
        if not requested_color:
            colors = {'red','blue','green','black','white','pink','yellow','navy','beige','brown','grey','gray','maroon','orange','purple'}
            query_colors = set(re.findall(r'[a-z]+', filters['event'].casefold())) & colors
            if len(query_colors) == 1: requested_color = next(iter(query_colors))
        candidates = {}
        failures = 0
        discovery_error = None
        try:
            status, home, _ = await self.transport.get(root+'/', max_bytes=4*1024*1024)
            if status != 200:
                raise ValueError(f'Storefront HTTP {status}; no bypass attempted')
            currency = storefront_currency(home.decode('utf-8', 'replace'))
            for page in range(1, MAX_PAGES+1):
                try:
                    url = root+f'/products.json?limit={PAGE_SIZE}'+(f'&page={page}' if page > 1 else '')
                    status, body, _ = await self.transport.get(url, max_bytes=8*1024*1024)
                    if status != 200:
                        raise ValueError(f'Feed HTTP {status}; no bypass attempted')
                    payload = json.loads(body)
                    rows = payload.get('products') if isinstance(payload, dict) else None
                    if not isinstance(rows, list):
                        raise ValueError('Expected public product feed; challenge or changed response rejected')
                    stamp = now_utc()
                    self.status.update(checked_at=stamp, pages=page)
                    for raw in rows[:PAGE_SIZE]:
                        self.status['scanned'] += 1
                        try:
                            product = parse_product(raw, self.source_name, currency, stamp, requested_color)
                            if product and SearchEngine.matches(product, **filters):
                                candidates[product.source_url] = product
                        except (TypeError, ValueError, KeyError, AttributeError):
                            continue  # malformed records do not discard the whole store
                    if len(rows) < PAGE_SIZE or len(candidates) >= max_images:
                        break
                except Exception as exc:
                    if not self.status['pages']:
                        raise
                    discovery_error = str(exc)[:250]
                    break
            self.status['found'] = len(candidates)
            attempts = 0
            for product in sorted(candidates.values(), key=lambda p:(p.price, p.title)):
                if len(self.products) >= max_images or attempts >= MAX_IMAGE_ATTEMPTS:
                    break
                attempts += 1
                try:
                    product.image_path = await self.transport.download_image(product.image_url)
                    product.metadata['image_validated'] = True
                    self.products.append(product)
                    self.status['usable'] = len(self.products)
                except Exception as exc:
                    failures += 1
                    self.status['last_image_error'] = str(exc)[:250]
            self.status.update(status='partial' if discovery_error else ('ok' if self.products else 'empty'),
                message=f"Fetched {self.status['scanned']} records across {self.status['pages']} page(s); "
                        f"{len(candidates)} match filters; {len(self.products)} usable photos; {failures} image failures. "
                        f"Limited to {MAX_PAGES*PAGE_SIZE} records / {max_images} photos per store."
                        +(f' Later page failed: {discovery_error}' if discovery_error else ''))
        except asyncio.CancelledError:
            self.status.update(status='timeout', message='Source deadline reached; only already downloaded fresh products retained')
            raise
        except Exception as exc:
            self.status.update(status='error', message=f'{type(exc).__name__}: {exc}'[:1000])
        return self.products

"""Filter-preserving search; budgets are INR, including decimals and Indian commas."""
import re
from clothing_pipeline.database.operations import ProductDB
from clothing_pipeline.cache.lru_cache import QueryCache
from clothing_pipeline.config import OCCASION_MAP, DEFAULT_OCCASION
from clothing_pipeline.validation import infer_category


class SearchEngine:
    def __init__(self, db=None, cache=None):
        self.db = db or ProductDB()
        self.cache = cache or QueryCache(self.db)

    @staticmethod
    def parse_budget(budget):
        if budget is None or not str(budget).strip():
            return None, None
        text = re.sub(r'(?:₹|\bINR\b|\bRs\.?\s*)', '', str(budget), flags=re.I).strip().lower()
        text = text.replace(',', '')
        number = r'(\d+(?:\.\d{1,2})?)'
        m = re.fullmatch(r'(?:under|below|max|upto|up\s+to)\s*'+number, text)
        if m: return None, float(m[1])
        m = re.fullmatch(r'(?:above|over|min|from)\s*'+number, text)
        if m: return float(m[1]), None
        m = re.fullmatch(number+r'\s*(?:-|–|—|to)\s*'+number, text)
        if m: return tuple(sorted((float(m[1]), float(m[2]))))
        m = re.fullmatch(number, text)
        if m: return None, float(m[1])
        raise ValueError('Use an INR budget like 5000, under 3,000, or 1500-5000; not negative amounts or other currencies.')

    @staticmethod
    def get_occasion_info(event):
        event = (event or '').strip().casefold()
        for key in sorted(OCCASION_MAP, key=len, reverse=True):
            if re.search(r'\b'+re.escape(key)+r'\b', event):
                return {**OCCASION_MAP[key], 'known': True}
        return {**DEFAULT_OCCASION, 'keywords': [event] if event else [], 'occasion_tag': event, 'known': False}

    def get_search_keywords(self, event):
        # Keep user-specified garment/color words rather than always substituting broad occasion text.
        return [(event or '').strip()]

    @classmethod
    def matches(cls, product, event='', budget='', brand=None, category=None, color=None, source=None, **_):
        lo, hi = cls.parse_budget(budget)
        if product.currency != 'INR': return False
        if lo is not None and (product.price is None or product.price < lo): return False
        if hi is not None and (product.price is None or product.price > hi): return False
        for name, val in (('brand',brand),('category',category),('source',source)):
            if val and (getattr(product,name) or '').casefold() != val.casefold(): return False
        if color and not re.search(r'\b'+re.escape(color.casefold())+r'\b', ((product.color or '')+' '+product.title).casefold()): return False
        event = (event or '').strip()
        if not event: return True
        info = cls.get_occasion_info(event)
        inferred = infer_category(event)
        if inferred != 'clothing' and (product.category or '') != inferred: return False
        text = ' '.join(str(x or '') for x in (product.title, product.brand, product.category, product.color, product.occasion)).casefold()
        if info['known']:
            colors = {'red','blue','green','black','white','pink','yellow','navy','beige','brown','grey','gray','maroon','orange','purple'}
            requested_colors = set(re.findall(r'[a-z]+', event.casefold())) & colors
            if any(not re.search(r'\b'+re.escape(c)+r'\b', text) for c in requested_colors): return False
            return product.occasion == info['occasion_tag'] or product.category in info['categories']
        words = re.findall(r'[a-z0-9]+', event.casefold())
        ignored = {'a','an','the','for','wear','outfit','clothes','clothing'}
        words = [w for w in words if w not in ignored]
        return not words or all(w in text or (inferred != 'clothing' and infer_category(w) == inferred) for w in words)

    def search(self, event=None, budget=None, brand=None, category=None, color=None, source=None, limit=50, use_cache=True):
        if not 1 <= limit <= 100: raise ValueError('limit must be 1..100')
        self.parse_budget(budget)
        params = dict(event=event or '', budget=budget or '', brand=brand, category=category, color=color, source=source, limit=limit)
        ids = self.cache.get(params) if use_cache else None
        if ids is not None:
            products = self.db.get_products_by_ids(ids)
            # Recheck actual current prices and filters even on a cache hit.
            filtered = [p for p in products if self.matches(p, **params)]
            if filtered: return filtered[:limit]
        lo, hi = self.parse_budget(budget)
        candidates = self.db.search_products(min_price=lo,max_price=hi,brand=brand,category=category,source=source,limit=2000)
        products = [p for p in candidates if self.matches(p, **params)]
        info = self.get_occasion_info(event)
        products.sort(key=lambda p:(p.occasion != info['occasion_tag'], p.price is None, p.price or 0, p.id or 0))
        products = products[:limit]
        if use_cache and products: self.cache.put(params,[p.id for p in products])
        return products

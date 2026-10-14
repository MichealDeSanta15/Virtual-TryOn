"""Thread-safe catalog API; no placeholder fallback and no silent filter relaxation."""
import asyncio
import os
import threading
from pathlib import Path
from clothing_pipeline.config import DB_PATH, IMAGE_DIR
from clothing_pipeline.database.operations import ProductDB
from clothing_pipeline.search.engine import SearchEngine
from clothing_pipeline.validation import verify_local_image, tryon_category
from clothing_pipeline.scraper.sources import ALL_SOURCES
from datetime import datetime, timezone


def run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        coro.close()
        raise RuntimeError('Call this synchronous search from a worker thread, not an asyncio event loop')
    # Playwright needs subprocess-capable Proactor on Windows even when the server
    # chose a Selector policy for its own event loop. This loop lives in the search worker.
    loop = asyncio.ProactorEventLoop() if os.name == 'nt' else asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending: task.cancel()
        if pending: loop.run_until_complete(asyncio.gather(*pending,return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
        asyncio.set_event_loop(None)
        loop.close()


class ClothingPipeline:
    def __init__(self, db_path=None, image_dir=None):
        self.db = ProductDB(db_path=Path(db_path or DB_PATH))
        self.engine = SearchEngine(self.db)
        self.image_dir = Path(image_dir or IMAGE_DIR)
        self.search_lock = threading.Lock()

    def _usable(self, products):
        results = []
        for p in products:
            if not p.image_path or (p.metadata or {}).get('is_placeholder') or p.source == 'fallback': continue
            try: verify_local_image(p.image_path, self.image_dir)
            except (OSError, ValueError): continue
            d = p.to_dict()
            d['tryon_category'] = tryon_category(p.category, p.title)
            d['tryon_supported'] = d['tryon_category'] is not None
            d['image_validated'] = True
            d['observed_at'] = (p.metadata or {}).get('observed_at')
            d['available_at_fetch'] = (p.metadata or {}).get('available_at_fetch')
            d['price_note'] = (p.metadata or {}).get('price_note')
            d['quality_note'] = 'Image decodes correctly; inspect garment framing, pose, lighting and image rights before trying on.'
            results.append(d)
        return results

    def search_report(self, event, budget, *, brand=None, category=None, color=None, source=None,
                      scrape_if_empty=True, refresh=False, limit=24, progress=None):
        event = str(event or '').strip()
        if not event or len(event)>160: raise ValueError('Enter an occasion or garment query (1..160 characters)')
        self.engine.parse_budget(budget)
        if source is not None and source not in ALL_SOURCES: raise ValueError('Unknown source')
        if not 1 <= limit <= 100: raise ValueError('limit must be 1..100')
        notify = progress or (lambda stage:None)
        filters = dict(event=event,budget=budget,brand=brand,category=category,color=color,source=source,limit=limit)
        started_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
        with self.search_lock:
            statuses = []
            used_live = bool(scrape_if_empty and source != 'local')
            results = []
            if used_live:
                # Historical parameter names retained for callers. Live ALWAYS fetches;
                # refresh=False can no longer allow saved records to mask a failed fetch.
                notify('searching_live_stores')
                try:
                    from clothing_pipeline.scraper import ScraperOrchestrator
                    orchestrator = ScraperOrchestrator(self.db, [source] if source else None,
                                                       self.image_dir, filters=filters)
                    query = ' '.join(x for x in (brand, event, category, color) if x)
                    fresh = run_async(orchestrator.scrape_all(query))
                    statuses = orchestrator.last_status
                    matching = [p for p in fresh if self.engine.matches(p, **filters)]
                    matching.sort(key=lambda p:(p.price is None, p.price or 0, p.id or 0))
                    # Do not search the entire database here: old matching rows are NOT live.
                    results = self._usable(matching)[:limit]
                except Exception as exc:
                    statuses = [{'source':source or 'all','status':'error','message':f'{type(exc).__name__}: {exc}'[:1000]}]
            else:
                notify('searching_saved_catalog')
                results = self._usable(self.engine.search(**filters))
            for product in results:
                product['freshness'] = 'fetched_this_search' if used_live else 'saved_observation'
            notify('catalog_ready')
            message = (f'{len(results)} matching products fetched during this search with validated photos.' if used_live else
                       f'{len(results)} matching saved products. No live availability check.') if results else (
                       'No matching live products with usable photos. No saved results substituted. Check source status, try a simpler query or another budget/source.' if used_live else
                       'No matching saved products with usable photos. Enable live search or upload a garment.')
            return {'products':results,'sources':statuses,'used_live':used_live,
                    'mode':'live' if used_live else 'local_cache', 'started_at':started_at,
                    'completed_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
                    'message':message, 'currency':'INR','query':event,'budget':str(budget or ''),
                    'notice':'Live means fetched during this search, not guaranteed stock or an uncached retailer backend. Feed discovery is bounded; not every product is scanned. Verify variant, availability, final price and image rights at retailer.'}

    def get_product(self, product_id):
        products = self._usable(self.db.get_products_by_ids([int(product_id)]))
        return products[0] if products else None


_instances = {}
_instance_lock = threading.Lock()

def get_pipeline():
    key = str(DB_PATH.resolve())
    with _instance_lock:
        if key not in _instances: _instances[key] = ClothingPipeline()
        return _instances[key]


def search_clothes(event, budget, **kwargs):
    """Original API retained. Returns real numeric-price products, never demo cards."""
    return get_pipeline().search_report(event,budget,**kwargs)['products']


def get_product(product_id): return get_pipeline().get_product(product_id)
def clear_cache(): get_pipeline().db.clear_cache()
def get_stats():
    db = get_pipeline().db
    return {'total_products':db.count_products(),'cache_entries':db.cache_entry_count(),
            'sources':{s:db.count_products(source=s) for s in ALL_SOURCES}}

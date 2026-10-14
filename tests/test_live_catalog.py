"""Deterministic live-first regressions. Synthetic fixtures never ship as catalog data."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import pytest
pytest.importorskip('requests')
pytest.importorskip('protego')
from PIL import Image
from clothing_pipeline.api import ClothingPipeline
from clothing_pipeline.database.models import Product
from clothing_pipeline.scraper import ScraperOrchestrator
from clothing_pipeline.scraper.shopify import (parse_product, feed_price, storefront_currency,
                                               PublicFeedScraper, image_url)
from clothing_pipeline.scraper.sources import DEFAULT_SOURCES
from clothing_pipeline.scraper.network import SafeTransport, allowed_url, _RATE_BLOCKED
from clothing_pipeline.scraper.public_http import PublicHTTPSConnection
from clothing_pipeline.validation import infer_category
from edgeai.server import CatalogRequest


@pytest.fixture
def raw():
    return {'title':'Cotton Shirt', 'handle':'cotton-shirt', 'vendor':'Fixture', 'product_type':'Shirts',
            'images':[{'src':'https://cdn.shopify.com/fixture.jpg'}],
            'options':[{'name':'Color','position':1},{'name':'Size','position':2}],
            'variants':[{'id':1,'title':'Blue / M','option1':'Blue','option2':'M','available':True,
                         'price':'1299.50','featured_image':{'src':'https://cdn.shopify.com/blue.jpg'}},
                        {'id':2,'title':'Red / S','option1':'Red','option2':'S','available':True,
                         'price':'999.00','featured_image':{'src':'https://cdn.shopify.com/red.jpg'}}]}


def product(raw, **kw):
    return parse_product(raw, 'nobero', 'INR', '2026-10-15T00:00:00+00:00', **kw)


@pytest.mark.parametrize('value,expected', [('1299.50',1299.5),('0',None),('-1',None),('₹99',None),
    ('NaN',None),('inf',None),('10.999',None),(True,None),(None,None),('1e4',None)])
def test_strict_feed_price(value, expected):
    assert feed_price(value) == expected


def test_currency_is_verified_not_assumed():
    assert storefront_currency('Shopify.currency = {"active":"INR","rate":"1.0"};') == 'INR'
    for text in ['<html>captcha</html>', 'Shopify.currency = {"active":"USD"};']:
        with pytest.raises(ValueError): storefront_currency(text)


def test_available_variant_price_color_size_and_image(raw):
    p = product(raw, color='Blue')
    assert p.price == 1299.5 and p.color == 'Blue' and p.sizes == ['M']
    assert '/blue.jpg' in p.image_url and 'width=1024' in p.image_url
    assert p.metadata['variant_id'] == 1 and p.metadata['available_at_fetch'] is True
    assert p.metadata['observed_at'] == '2026-10-15T00:00:00+00:00'
    assert p.source_url == 'https://nobero.com/products/cotton-shirt'
    assert product(raw).price == 999
    raw['variants'][1]['available'] = False
    assert product(raw).price == 1299.5
    assert product(raw, color='red') is None
    raw['variants'][0]['available'] = False
    assert product(raw) is None


def test_multicolor_without_matching_photo_is_not_guessed(raw):
    for v in raw['variants']: v['featured_image'] = None
    assert product(raw, color='blue') is None
    raw['variants'] = raw['variants'][:1]
    assert product(raw, color='blue') is not None


@pytest.mark.parametrize('title,kind', [('Bundle','Shirt Set'),('Kids Cotton Shirt','Shirts'),
    ('Matching outfit','Womens Looks'),('Two-piece','Co-ord Set'),('Cotton socks','Accessories')])
def test_unsupported_sets_children_accessories_excluded(raw, title, kind):
    raw.update(title=title,product_type=kind)
    assert product(raw) is None


def test_title_category_not_overridden_by_query_or_length(raw):
    assert infer_category('Cotton Linen Beige Tiered Maxi Skirt') == 'skirt'
    assert infer_category('Midi skirt') == 'skirt'
    assert infer_category('Maxi dress') == 'dress'
    raw.update(title='Ayla',product_type='Dresses')
    assert product(raw).category == 'dress'
    raw.update(title='Cotton T-shirt Dress',product_type='Shirts')
    assert product(raw).category == 'dress'


def test_unsafe_handle_photo_currency_rejected(raw):
    raw['handle'] = '../../account'
    assert product(raw) is None
    assert image_url('https://cdn.shopify.com.evil.test/x') is None
    assert image_url('https://127.0.0.1/image') is None
    assert image_url('//cdn.shopify.com/test?width=5000').endswith('width=1024')
    assert parse_product(raw,'nobero','USD','now') is None
    assert allowed_url('https://www.femmella.com/products/test')


@pytest.fixture
def pipe(tmp_path):
    return ClothingPipeline(tmp_path/'db.sqlite',tmp_path/'images')


def seed(pipe, title, source='nobero'):
    pipe.image_dir.mkdir(parents=True,exist_ok=True)
    path = pipe.image_dir/(title.replace(' ','-')+'.png')
    Image.new('RGB',(100,150),'blue').save(path)
    p = Product(source=source,source_url='https://nobero.com/products/'+title.replace(' ','-'),
                title=title,category='shirt',currency='INR',price=1200,image_path=str(path),
                metadata={'observed_at':'2000-01-01T00:00:00+00:00'})
    p.id = pipe.db.insert_product(p)
    return p


def test_live_always_refetches_and_never_leaks_saved_rows(pipe, monkeypatch):
    old = seed(pipe,'Old Shirt')
    fresh = seed(pipe,'Fresh Shirt')
    calls = []
    async def scrape(self, query):
        calls.append(query)
        self.last_status = [{'source':'nobero','status':'ok'}]
        return [fresh]
    monkeypatch.setattr(ScraperOrchestrator,'scrape_all',scrape)
    for _ in range(2):
        report = pipe.search_report('shirt','5000',refresh=False)
        assert [p['id'] for p in report['products']] == [fresh.id]
        assert report['mode'] == 'live'
        assert report['products'][0]['freshness'] == 'fetched_this_search'
    assert len(calls) == 2
    async def fail(self, query): raise ValueError('HTTP 429')
    monkeypatch.setattr(ScraperOrchestrator,'scrape_all',fail)
    assert pipe.search_report('shirt','5000')['products'] == []
    saved = pipe.search_report('shirt','5000',scrape_if_empty=False)
    assert saved['mode']=='local_cache' and len(saved['products'])==2
    assert all(p['freshness']=='saved_observation' for p in saved['products'])


def test_live_does_not_relax_filters(pipe, monkeypatch):
    p=seed(pipe,'Cotton Shirt')
    async def scrape(self,q): return [p]
    monkeypatch.setattr(ScraperOrchestrator,'scrape_all',scrape)
    assert pipe.search_report('shirt','100')['products'] == []
    assert pipe.search_report('dress','5000')['products'] == []
    assert pipe.search_report('shirt','5000',brand='Missing')['products'] == []
    with pytest.raises(ValueError): pipe.search_report('shirt','5000',limit=0)


def test_live_default_and_default_sources():
    assert CatalogRequest(event='shirt').live is True
    assert set(ScraperOrchestrator().sources)==set(DEFAULT_SOURCES)
    assert not set(DEFAULT_SOURCES) & {'amazon','ajio','myntra'}
    for source in DEFAULT_SOURCES:
        assert CatalogRequest(event='shirt',source=source).source == source


class FeedTransport:
    def __init__(self, raw, tmp_path):
        self.raw=raw; self.calls=[]; self.downloads=[]; self.tmp_path=tmp_path
    async def get(self,url,**kw):
        self.calls.append(url)
        if '/products.json?' in url: return 200,json.dumps({'products':[self.raw]}).encode(),url
        return 200,b'Shopify.currency = {"active":"INR"};',url
    async def download_image(self,url):
        self.downloads.append(url)
        p=self.tmp_path/'photo.png';Image.new('RGB',(100,150)).save(p)
        return str(p)


def test_feed_filters_before_image_downloads(raw,tmp_path):
    t=FeedTransport(raw,tmp_path)
    s=PublicFeedScraper('nobero',t,{'event':'shirt','budget':'100'})
    assert asyncio.run(s.scrape('shirt')) == []
    assert len(t.calls)==2 and t.downloads==[] and s.status['status']=='empty'


def test_color_in_query_selects_corresponding_variant(raw,tmp_path):
    t=FeedTransport(raw,tmp_path)
    s=PublicFeedScraper('nobero',t,{'event':'blue shirt','budget':'5000'})
    p=asyncio.run(s.scrape('blue shirt'))[0]
    assert p.color=='Blue' and '/blue.jpg' in t.downloads[0]
    assert s.status['checked_at'] and s.status['usable']==1


def test_partial_discovery_preserves_only_completed_fresh_products(raw,tmp_path,monkeypatch):
    import clothing_pipeline.scraper.shopify as feed
    monkeypatch.setattr(feed,'PAGE_SIZE',1)
    t=FeedTransport(raw,tmp_path)
    original=t.get
    async def get(url,**kw):
        if '&page=2' in url: return 403,b'blocked',url
        return await original(url,**kw)
    t.get=get
    s=PublicFeedScraper('nobero',t,{'event':'shirt','budget':'5000'})
    assert len(asyncio.run(s.scrape('shirt')))==1
    assert s.status['status']=='partial' and '403' in s.status['message']


def test_feed_challenge_is_not_products(raw,tmp_path):
    t=FeedTransport(raw,tmp_path)
    async def get(url,**kw): return 200,b'<html>verify you are human</html>',url
    t.get=get
    s=PublicFeedScraper('nobero',t,{'event':'shirt'})
    assert asyncio.run(s.scrape('shirt'))==[]
    assert s.status['status']=='error' and t.downloads==[]


def test_network_redirect_and_cooldown_guards(tmp_path,monkeypatch):
    import clothing_pipeline.scraper.public_http as http
    from clothing_pipeline.scraper.network import RateLimiter
    async def no_wait(self): pass
    monkeypatch.setattr(RateLimiter,'wait',no_wait)
    calls=[]
    def get(url,max_bytes):
        calls.append(url)
        return 302,b'',{'Location':'http://127.0.0.1/private'}
    monkeypatch.setattr(http,'fetch_public',get)
    async def run():
        async with SafeTransport(tmp_path) as t:
            with pytest.raises(ValueError):
                await t.get('https://nobero.com/test',respect_robots=False)
        assert len(calls)==1
        def limited(url,max_bytes):
            calls.append(url)
            return 429,b'limited',{'Retry-After':'120'}
        monkeypatch.setattr(http,'fetch_public',limited)
        async with SafeTransport(tmp_path) as t:
            assert (await t.get('https://nobero.com/test',respect_robots=False))[0]==429
            with pytest.raises(ValueError,match='cooldown'):
                await t.get('https://nobero.com/test',respect_robots=False)
        assert len(calls)==2
    try: asyncio.run(run())
    finally: _RATE_BLOCKED.pop('nobero.com',None)


def test_connection_rejects_private_or_mixed_dns(monkeypatch):
    import clothing_pipeline.scraper.public_http as http
    for addresses in [['127.0.0.1'],['8.8.8.8','169.254.169.254']]:
        monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**kw:[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443)) for ip in addresses])
        with pytest.raises(OSError,match='Non-public'): PublicHTTPSConnection('nobero.com')._new_conn()
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**kw:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',443))])
    calls=[]
    monkeypatch.setattr(http,'create_connection',lambda addr,*a:(calls.append(addr) or 'socket-fixture'))
    conn=PublicHTTPSConnection('nobero.com')
    assert conn._new_conn()=='socket-fixture'
    assert calls==[('8.8.8.8',443)] and conn.host=='nobero.com'


def test_orchestrator_isolates_one_failed_store(pipe, monkeypatch):
    from clothing_pipeline.scraper.shopify import PublicFeedScraper
    p=seed(pipe,'Independent Shirt')
    async def scrape(self,query):
        if self.source_name=='nonasties': raise RuntimeError('blocked test store')
        rows=[p] if self.source_name=='nobero' else []
        self.status.update(status='ok' if rows else 'empty',usable=len(rows))
        return rows
    monkeypatch.setattr(PublicFeedScraper,'scrape',scrape)
    report=pipe.search_report('shirt','5000')
    assert len(report['products'])==1 and report['products'][0]['source']=='nobero'
    assert next(s for s in report['sources'] if s['source']=='nonasties')['status']=='error'
    assert len(report['sources'])==4

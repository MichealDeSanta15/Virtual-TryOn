"""Catalog regressions and handoff tests. No retailer network or learned AI needed."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import asyncio
import json
from pathlib import Path
import pytest
pytest.importorskip("aiohttp")
pytest.importorskip("protego")
from PIL import Image
from fastapi.testclient import TestClient
from edgeai.server import create_app
from edgeai.config import Settings
from clothing_pipeline.api import ClothingPipeline, run_async
from clothing_pipeline.cache.lru_cache import QueryCache
from clothing_pipeline.database.models import Product
from clothing_pipeline.database.operations import ProductDB
from clothing_pipeline.database.schema import initialize_database
from clothing_pipeline.search.engine import SearchEngine
from clothing_pipeline.validation import clean_price, infer_category, normalized_image, tryon_category
from clothing_pipeline.importer import import_manifest
from clothing_pipeline.scraper.network import allowed_url
from clothing_pipeline.scraper.robots import RobotsChecker


@pytest.mark.parametrize('text,expected',[
 ('₹1,299.50',1299.5),('Rs. 2,499',2499),('999.99',999.99),('',None)])
def test_retail_price_decimal(text,expected): assert clean_price(text)==expected

@pytest.mark.parametrize('text,expected',[
 ('under 3,000',(None,3000)),('₹1,299.50',(None,1299.5)),('above 3000',(3000,None)),
 ('Rs. 1,00,000',(None,100000)),('1000 to 3000',(1000,3000)),('5000-2000',(2000,5000))])
def test_catalog_budget(text,expected): assert SearchEngine.parse_budget(text)==expected

@pytest.mark.parametrize('text',['abc','-500','USD 20','$50','free','NaN'])
def test_budget_rejects_invalid(text):
 with pytest.raises(ValueError): SearchEngine.parse_budget(text)


def test_category_priority_and_unsupported_sets():
 assert infer_category('Cotton T-shirt','shirt')=='t-shirt'
 assert infer_category('Floral Maxi Dress','shirt')=='dress'
 assert infer_category('T-shirt Dress','top')=='dress'
 assert tryon_category('dress','Maxi dress')=='overall'
 assert tryon_category('kurta','Kurta set') is None
 assert tryon_category('saree','Silk saree') is None


@pytest.fixture
def pipeline(tmp_path): return ClothingPipeline(tmp_path/'catalog.db',tmp_path/'images')


def put_product(pipe, title='Red party dress', price=1500, category='dress', color='red', source='local', brand='Test', occasion='party', url=None):
 pipe.image_dir.mkdir(exist_ok=True,parents=True)
 image=Image.new('RGB',(120,160),(100,110,120))
 path=pipe.image_dir/(title.replace(' ','_')+'.png');image.save(path)
 item=Product(source=source,source_url=url or 'local://'+title,title=title,price=price,brand=brand,
              category=category,color=color,occasion=occasion,image_path=str(path.resolve()),metadata={'is_placeholder':False})
 return pipe.db.insert_product(item)


def test_upsert_returns_stable_id(pipeline):
 a=put_product(pipeline,title='A');b=put_product(pipeline,title='B')
 again=put_product(pipeline,title='A',price=1234)
 assert a==again and b!=a
 assert pipeline.db.get_product_by_id(a).price==1234


def test_filters_never_relaxed(pipeline):
 put_product(pipeline)
 put_product(pipeline,title='Blue party dress',price=7000,brand='Other',color='blue',source='myntra')
 for kwargs in [dict(brand='Missing'),dict(color='green'),dict(category='jeans'),dict(source='ajio')]:
  assert pipeline.search_report('party','5000',scrape_if_empty=False,**kwargs)['products']==[]
 results=pipeline.search_report('freshers red dress','5000',scrape_if_empty=False)['products']
 assert len(results)==1 and results[0]['title']=='Red party dress'


def test_new_price_rechecked_on_cache_hit(pipeline):
 pid=put_product(pipeline)
 assert pipeline.engine.search(event='party',budget='2000')
 item=pipeline.db.get_product_by_id(pid);item.price=9000;pipeline.db.insert_product(item)
 assert pipeline.engine.search(event='party',budget='2000')==[]


def test_ttl_and_lru(pipeline):
 cache=QueryCache(pipeline.db,max_entries=2)
 cache.put({'a':1},[1]);cache.put({'a':2},[2]);cache.put({'a':3},[3])
 assert pipeline.db.cache_entry_count()==2
 assert cache.get({'a':1}) is None
 conn=initialize_database(pipeline.db.db_path)
 conn.execute("UPDATE cache_entries SET created_at='2000-01-01 00:00:00'");conn.commit();conn.close()
 assert cache.get({'a':3}) is None


def test_pipeline_database_works_across_threads(pipeline):
 put_product(pipeline)
 def search(_): return pipeline.search_report('party','5000',scrape_if_empty=False)['products']
 with ThreadPoolExecutor(max_workers=4) as executor:
  assert all(len(x)==1 for x in executor.map(search,range(8)))


def test_no_generated_fallback_or_missing_images(pipeline):
 assert pipeline.search_report('party','5000',scrape_if_empty=False)['products']==[]
 pid=put_product(pipeline)
 product=pipeline.db.get_product_by_id(pid)
 Path(product.image_path).unlink()
 assert pipeline.search_report('party','5000',scrape_if_empty=False)['products']==[]
 put_product(pipeline,title='Placeholder',source='fallback')
 assert pipeline.search_report('party','5000',scrape_if_empty=False)['products']==[]


def test_count_filter_identifier_validation(pipeline):
 with pytest.raises(ValueError): pipeline.db.count_products(**{'source); DROP TABLE products; --':'x'})


def test_image_validation_and_alpha():
 with pytest.raises(ValueError): normalized_image(b'<html>blocked</html>')
 small=BytesIO();Image.new('RGB',(10,10)).save(small,format='PNG')
 with pytest.raises(ValueError): normalized_image(small.getvalue())
 buf=BytesIO();Image.new('RGBA',(100,100),(0,0,0,0)).save(buf,format='PNG')
 assert normalized_image(buf.getvalue()).getpixel((0,0))==(255,255,255)


@pytest.mark.parametrize('url',[ 'http://127.0.0.1/a','http://169.254.169.254/latest/meta-data/',
 'file:///etc/passwd','https://www.myntra.com.evil.test/a','https://u:p@www.myntra.com/a','https://www.myntra.com:444/a'])
def test_remote_url_rejections(url): assert not allowed_url(url)


def test_remote_cdn_allowlist():
 assert allowed_url('https://assets.myntassets.com/example.jpg')
 assert allowed_url('https://m.media-amazon.com/images/I/example.jpg')


@pytest.mark.parametrize('status,body,allowed',[
 (200,b'User-agent: *\nDisallow: /search*',False),
 (200,b'User-agent: *\nAllow: /',True),(403,b'Forbidden',False),
 (500,b'Error',False),(404,b'Not found',True),(200,b'<html>captcha</html>',False),
 (200,b'{"error":"challenge"}',False)])
def test_robots_policy(status,body,allowed):
 class Transport:
  async def get(self,*args,**kwargs): return status,body,'https://www.ajio.com/robots.txt'
  def limiter(self,url):
   from types import SimpleNamespace
   return SimpleNamespace(min_delay=1)
 assert asyncio.run(RobotsChecker(Transport()).can_fetch('https://www.ajio.com/search/?text=dress')) is allowed


def test_manifest_requires_real_image_and_permission(tmp_path,pipeline):
 photo=tmp_path/'test-photo.png';Image.new('RGB',(120,160)).save(photo)
 entry={'title':'Fixture Dress','image_path':photo.name,'price':1234.5,'occasion':'party'}
 manifest=tmp_path/'catalog.json';manifest.write_text(json.dumps([entry]))
 with pytest.raises(ValueError,match='image_rights_confirmed'): import_manifest(manifest,pipeline)
 entry['image_rights_confirmed']=True;manifest.write_text(json.dumps([entry]))
 ids=import_manifest(manifest,pipeline)
 assert len(ids)==1
 assert pipeline.get_product(ids[0])['price']==1234.5
 assert pipeline.get_product(ids[0])['tryon_category']=='overall'


def test_search_failure_report_is_not_fake_products(pipeline,monkeypatch):
 from clothing_pipeline.scraper import ScraperOrchestrator
 async def fail(self,q): raise RuntimeError('retailer unreachable')
 monkeypatch.setattr(ScraperOrchestrator,'scrape_all',fail)
 report=pipeline.search_report('party','5000',scrape_if_empty=True)
 assert report['products']==[] and report['sources'][0]['status']=='error'


def test_catalog_http_handoff(tmp_path):
 class NoAI:
  pipeline=None
 app=create_app(Settings(data_dir=tmp_path/'data',model_dir=tmp_path/'models'),token='test-catalog-token-1234',engine=NoAI())
 headers={'Authorization':'Bearer test-catalog-token-1234'}
 with TestClient(app) as client:
  catalog=app.state.catalog
  pid=put_product(catalog.pipeline)
  assert client.post('/api/catalog/search',json={'event':'party','budget':'5000'}).status_code==401
  r=client.post('/api/catalog/search',headers=headers,json={'event':'party','budget':'5000','live':False})
  assert r.status_code==202
  app.state.catalog_worker.pending.join()
  job=client.get('/api/catalog/search/'+r.json()['id'],headers=headers).json()
  assert job['state']=='done'
  product=job['result']['products'][0]
  assert 'image_path' not in product  # no host filesystem path exposure
  assert client.get(f'/api/catalog/products/{pid}/image',headers=headers).status_code==200
  selection=client.post(f'/api/catalog/products/{pid}/select',headers=headers).json()
  assert selection['category']=='overall'
  assert client.get('/api/assets/'+selection['garment'],headers=headers).status_code==200
  # This actual asset ID is accepted by the existing try-on job API. No AI is mocked as a real result.
  request={'person':selection['garment'],'garment':selection['garment'],'category':'overall'}
  assert client.post('/api/jobs',headers=headers,json=request).status_code==202
  app.state.worker.pending.join()
  assert client.post('/api/catalog/search',headers=headers,json={'event':'party','budget':'invalid'}).status_code==400


def test_async_sync_bridge_does_not_nest_event_loops():
 async def noop(): return 1
 assert run_async(noop())==1
 async def outer():
  with pytest.raises(RuntimeError,match='worker thread'): run_async(noop())
 asyncio.run(outer())

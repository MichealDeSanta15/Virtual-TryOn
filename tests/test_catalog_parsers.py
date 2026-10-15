"""Offline DOM fixtures: verifies extraction code, not current retailer availability."""
import asyncio
from pathlib import Path
import pytest

playwright = pytest.importorskip('playwright.async_api')


def test_three_retailer_dom_fixtures():
 from clothing_pipeline.scraper.myntra import MyntraScraper
 from clothing_pipeline.scraper.ajio import AjioScraper
 from clothing_pipeline.scraper.amazon import AmazonScraper
 async def run():
  async with playwright.async_playwright() as pw:
   try: browser=await pw.chromium.launch(headless=True)
   except Exception as exc:
    if "Executable doesn't exist" in str(exc): pytest.skip('Install Chromium to run parser fixtures')
    raise
   try:
    page=await browser.new_page()
    for name,cls,price in [('myntra',MyntraScraper,1499.5),('ajio',AjioScraper,1599.75),('amazon',AmazonScraper,1299.5)]:
     await page.route('**/*',lambda route:route.abort())
     await page.set_content((Path(__file__).parent/'fixtures/catalog'/f'{name}.html').read_text())
     products=await cls(transport=None).parse_products(page,'party dress')
     assert len(products)==1
     p=products[0]
     assert p.price==price
     assert 'Maxi Dress' in p.title and p.title!='Fixture Brand'
     assert p.category=='dress'
     assert p.source_url.startswith('https://')
     assert p.image_url.startswith('https://') and not p.image_url.startswith('data:')
   finally: await browser.close()
 asyncio.run(run())

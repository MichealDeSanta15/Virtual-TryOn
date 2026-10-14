"""Adapter: catalog metadata -> validated local asset -> existing diffusion API."""
from pathlib import Path
from .imaging import load_rgb


class CatalogService:
    def __init__(self, settings, store):
        from clothing_pipeline.api import ClothingPipeline
        root = settings.data_dir/'catalog'
        self.pipeline = ClothingPipeline(root/'products.db',root/'images')
        self.store = store

    def public_product(self, item):
        return {key:item.get(key) for key in ('id','title','brand','price','currency','category','color',
            'occasion','source','source_url','updated_at','observed_at','freshness','available_at_fetch','price_note',
            'tryon_category','tryon_supported','quality_note')}

    def search(self, progress, **request):
        report = self.pipeline.search_report(progress=progress,**request)
        report['products'] = [self.public_product(item) for item in report['products']]
        return report

    def image_path(self, product_id):
        item = self.pipeline.get_product(product_id)
        if not item: raise FileNotFoundError('Product or its validated photo is missing')
        return Path(item['image_path'])

    def select(self, product_id):
        item = self.pipeline.get_product(product_id)
        if not item: raise FileNotFoundError('Product or image no longer exists')
        if not item['tryon_supported']:
            raise ValueError('This product category is not mapped to a supported single garment. Upload a suitable product photo manually instead.')
        asset = self.store.save(load_rgb(item['image_path']))
        return {'garment':asset,'source_garment':asset,'requires_preparation':True,
                'category':item['tryon_category'],'product':self.public_product(item)}

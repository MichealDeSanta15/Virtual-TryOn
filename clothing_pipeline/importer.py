"""Import a manifest of actual local garment photos; no fake prices/images bundled."""
import hashlib
import json
import math
from pathlib import Path
from clothing_pipeline.database.models import Product
from clothing_pipeline.validation import normalized_image, infer_category
from clothing_pipeline.config import MAX_CATALOG_BYTES


def import_manifest(path, pipeline):
    path = Path(path).resolve()
    entries = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(entries,list) or len(entries)>500: raise ValueError('Manifest must contain at most 500 product objects')
    products = []
    for i,item in enumerate(entries):
        if not isinstance(item,dict): raise ValueError(f'Entry {i+1} is not an object')
        if item.get('is_placeholder') or not item.get('title') or not item.get('image_path'):
            raise ValueError(f'Entry {i+1}: title and a real image_path are required')
        title = str(item['title']).strip()[:240]
        image_path = (path.parent / item['image_path']).resolve()
        # Manifest is a local CLI input, not an arbitrary path accepted by the HTTP API.
        if not image_path.is_file() or image_path.stat().st_size > 12*1024*1024:
            raise ValueError(f'Entry {i+1}: image missing or too large')
        image = normalized_image(image_path.read_bytes())
        value = item.get('price')
        price = float(value) if value is not None else None
        if price is not None and (not math.isfinite(price) or price <= 0): raise ValueError('Price must be positive or null')
        if item.get('currency','INR') != 'INR': raise ValueError('Only INR catalog prices supported')
        if not item.get('image_rights_confirmed',False):
            raise ValueError(f'Entry {i+1}: set image_rights_confirmed=true only if you have permission to use the photo')
        from io import BytesIO
        buf=BytesIO();image.save(buf,format='PNG');data=buf.getvalue()
        pipeline.image_dir.mkdir(parents=True,exist_ok=True)
        target=pipeline.image_dir/(hashlib.sha256(data).hexdigest()+'.png')
        if not target.exists():
            if sum(p.stat().st_size for p in pipeline.image_dir.glob('*.png'))+len(data)>MAX_CATALOG_BYTES:
                raise ValueError('Catalog image cache full')
            temp=target.with_suffix('.tmp');temp.write_bytes(data);temp.replace(target)
        local_key = hashlib.sha256((str(path)+':'+str(item.get('id',i))).encode()).hexdigest()
        products.append(Product(source='local',source_url='local://'+local_key,title=title,price=price,
            brand=item.get('brand'),category=item.get('category') or infer_category(title),
            color=item.get('color'),occasion=item.get('occasion'),image_path=str(target.resolve()),
            metadata={'origin':'local_manifest','image_rights_confirmed':True,'is_placeholder':False,
                      'original_source_url':item.get('source_url')}))
    ids=pipeline.db.bulk_insert(products)
    pipeline.db.clear_cache()
    return ids

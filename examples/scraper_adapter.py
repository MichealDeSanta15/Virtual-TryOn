"""Member 2 contract validation. This module does not scrape websites."""
from pathlib import Path
from edgeai.config import CATEGORIES


def validate_product(product):
    required=('image_path','title','price','tryon_category')
    missing=[key for key in required if key not in product]
    if missing:raise ValueError(f'Missing fields: {missing}')
    path=Path(product['image_path'])
    if not path.is_file():raise FileNotFoundError(path)
    if product['tryon_category'] not in CATEGORIES:raise ValueError('Use upper, lower or overall')
    if float(product['price'])<0:raise ValueError('Invalid price')
    return {**product,'image_path':str(path.resolve()),'price':float(product['price'])}

# Example expected scraper result:
# {"image_path":"catalog/blue-shirt.png", "title":"Blue cotton shirt",
#  "price":1299, "tryon_category":"upper", "currency":"INR"}
# Do not send a product webpage, a remote URL or an unresolved thumbnail path
# as image_path. Multi-model editorial photos make poor garment references.

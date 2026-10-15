"""Shared parsing and image contracts. No fake garments or invented prices."""
import re
import math
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageOps

# Match specific forms before substrings such as shirt/dress.
CATEGORY_RULES = [
    ('t-shirt', r'\bt[ -]?shirts?\b'), ('shirt', r'\bshirts?\b'),
    ('jeans', r'\bjeans\b'), ('trousers', r'\b(?:trousers?|pants?)\b'),
    ('dress', r'\b(?:dresses|dress|gowns?)\b'),
    ('saree', r'\b(?:sarees?|saris?)\b'), ('lehenga', r'\blehengas?\b'),
    ('suit', r'\b(?:suits?|co[ -]?ords?|sets?|jumpsuits?)\b'),
    ('anarkali', r'\banarkali\b'), ('kurta', r'\bkurt[ai]s?\b'),
    ('blazer', r'\bblazers?\b'), ('jacket', r'\bjackets?\b'),
    ('hoodie', r'\bhoodies?\b'), ('shorts', r'\bshorts\b'),
    ('skirt', r'\bskirts?\b'), ('top', r'\b(?:tops?|blouses?)\b'),
    ('sweater', r'\b(?:sweaters?|sweatshirts?)\b'), ('palazzo', r'\bpalazzos?\b'),
    ('chinos', r'\bchinos\b'), ('joggers', r'\bjoggers?\b'),
    ('leggings', r'\bleggings\b'), ('dupatta', r'\bdupattas?\b'),
]
GROUPS = {'upper': {'t-shirt','shirt','top','blouse','blazer','jacket','hoodie','sweater','kurta'},
          'lower': {'jeans','trousers','pants','skirt','shorts','palazzo','chinos','joggers','track pants','leggings'},
          'overall': {'dress','gown','anarkali'}}


def infer_category(title, query=''):
    # Query context must never overwrite an explicit category in the title.
    for text in (title, query):
        if re.search(r'\b(?:t[ -]?shirt|shirt) dress(?:es)?\b', text, re.I): return 'dress'
        for category, pattern in CATEGORY_RULES:
            if re.search(pattern, text, re.I):
                return category
        if re.search(r'\b(?:maxi|midi)\b', text, re.I): return 'dress'
    return 'clothing'


def tryon_category(category, title=''):
    # Multi-piece clothing is not silently labelled as a supported single dress.
    if re.search(r'\b(?:co[ -]?ord|set|suit|lehenga|saree|sari|dupatta|jumpsuit)\b', title, re.I):
        return None
    for group, names in GROUPS.items():
        if (category or '').casefold() in names:
            return group
    return None


def clean_price(text):
    if not text:
        return None
    # Preserve decimal point; do not treat '.' as a removable currency character.
    match = re.search(r'(?<!\d)(\d[\d,]*(?:\.\d{1,2})?)(?!\d)', str(text))
    if not match:
        return None
    value = float(match.group(1).replace(',', ''))
    return value if math.isfinite(value) and value > 0 else None


def normalized_image(data, max_bytes=12*1024*1024):
    if len(data) > max_bytes:
        raise ValueError('Image exceeds 12 MB limit')
    try:
        with Image.open(BytesIO(data)) as im:
            if im.format not in ('JPEG','PNG','WEBP'):
                raise ValueError('Only JPEG, PNG and WebP product photos are accepted')
            if im.width * im.height > 20_000_000 or min(im.size) < 96:
                raise ValueError('Product image is too small or exceeds 20 megapixels')
            im.load()
            im = ImageOps.exif_transpose(im)
            if im.mode in ('RGBA','LA') or 'transparency' in im.info:
                fg = im.convert('RGBA')
                image = Image.new('RGB', fg.size, 'white')
                image.paste(fg, mask=fg.getchannel('A'))
            else:
                image = im.convert('RGB')
            image.thumbnail((2048,2048), Image.Resampling.LANCZOS)
            return image
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError('Downloaded data is not a usable product image') from exc


def verify_local_image(path, root=None):
    p = Path(path).resolve()
    if root and not p.is_relative_to(Path(root).resolve()):
        raise ValueError('Product path is outside the catalog image directory')
    if not p.is_file() or p.stat().st_size > 12*1024*1024:
        raise ValueError('Product image is missing or too large')
    return normalized_image(p.read_bytes())

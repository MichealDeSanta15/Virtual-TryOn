"""No arbitrary client-supplied file paths. Explicit, bounded local persistence."""
from pathlib import Path
from io import BytesIO
import threading
import uuid
from PIL import Image, ImageOps, UnidentifiedImageError
from .imaging import to_rgb_white


class Storage:
    def __init__(self, root, max_mb=15):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_mb * 1024**2
        self.lock = threading.Lock()

    def path(self, key):
        if len(key) != 32 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError("Invalid asset ID")
        path = self.root / f"{key}.png"
        if not path.is_file():
            raise FileNotFoundError("Asset no longer exists")
        return path

    def save(self, image):
        with self.lock:
            files = list(self.root.glob("*.png"))
            if len(files) >= 180 or sum(p.stat().st_size for p in files) > 768 * 1024**2:
                raise ValueError("Local storage full. Use Clear session files before continuing.")
            key = uuid.uuid4().hex
            image.save(self.root / f"{key}.png")
            return key

    def upload(self, data, mask=False):
        if len(data) > self.max_bytes:
            raise ValueError("Upload is too large")
        try:
            with Image.open(BytesIO(data)) as im:
                if im.width * im.height > 20_000_000 or min(im.size) < 16:
                    raise ValueError("Image must be 16px or larger and at most 20 megapixels")
                im.load()
                oriented = ImageOps.exif_transpose(im)
                image = oriented.convert("L") if mask else to_rgb_white(oriented)
                if max(image.size) > 2048:
                    # Do not silently resize masks and break image correspondence.
                    raise ValueError("Resize image to at most 2048 pixels on its longest side")
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("Upload must be a valid PNG, JPEG or WebP image") from exc
        return self.save(image)

    def clear(self):
        with self.lock:
            for path in self.root.glob("*.png"):
                path.unlink(missing_ok=True)

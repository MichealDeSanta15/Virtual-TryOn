"""Explicit RGB/PIL <-> BGR/OpenCV boundaries and reversible geometry."""
from dataclasses import dataclass
import numpy as np
import cv2
from PIL import Image, ImageOps


def bgr_to_pil(frame):
    if not isinstance(frame, np.ndarray) or frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Expected H x W x 3 uint8 BGR frame")
    return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))


def pil_to_bgr(image):
    return cv2.cvtColor(np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR)


def load_rgb(path):
    with Image.open(path) as image:
        return to_rgb_white(ImageOps.exif_transpose(image))

def to_rgb_white(image):
    if image.mode in ('RGBA', 'LA') or 'transparency' in image.info:
        rgba = image.convert('RGBA')
        out = Image.new('RGB', image.size, 'white')
        out.paste(rgba, mask=rgba.getchannel('A'))
        return out
    return image.convert('RGB')

@dataclass(frozen=True)
class Letterbox:
    original: tuple
    target: tuple
    box: tuple

    @classmethod
    def create(cls, original, target):
        w, h = original
        tw, th = target
        scale = min(tw / w, th / h)
        rw, rh = max(1, round(w * scale)), max(1, round(h * scale))
        x, y = (tw - rw) // 2, (th - rh) // 2
        return cls(original, target, (x, y, x + rw, y + rh))

    def apply(self, image, mask=False):
        if image.size != self.original:
            raise ValueError("Mask/image geometry mismatch")
        mode = "L" if mask else "RGB"
        canvas = Image.new(mode, self.target, 0 if mask else (245, 245, 245))
        x, y, r, b = self.box
        small = image.convert(mode).resize((r-x, b-y), Image.Resampling.NEAREST if mask else Image.Resampling.LANCZOS)
        canvas.paste(small, (x, y))
        return canvas

    def restore(self, image, mask=False):
        return image.crop(self.box).resize(self.original, Image.Resampling.NEAREST if mask else Image.Resampling.LANCZOS)


def validate_mask(mask, expected):
    if mask.size != expected:
        raise ValueError("Mask must have exactly the person image dimensions")
    arr = np.asarray(mask.convert("L")) > 127
    coverage = float(arr.mean())
    if coverage < .001:
        raise ValueError("Empty / too-small mask. Paint the garment region first.")
    if coverage > .85:
        raise ValueError("Mask covers almost the entire person image. Protect face and background.")
    return Image.fromarray(arr.astype(np.uint8) * 255)


def preserve_outside(original, generated, mask):
    """Blend generated *person* pixels, never paste or warp the product photo.

    Feather inwards only: outside-mask pixels are bit-exact original pixels.
    """
    orig = np.asarray(original.convert("RGB"))
    gen = np.asarray(generated.convert("RGB"))
    binary = (np.asarray(mask.convert("L")) > 127).astype(np.uint8)
    distance = cv2.distanceTransform(binary, cv2.DIST_L2, 3)
    feather = max(2, min(original.size) / 150)
    alpha = np.clip(distance / feather, 0, 1)[..., None]
    return Image.fromarray(np.rint(gen * alpha + orig * (1-alpha)).astype(np.uint8))

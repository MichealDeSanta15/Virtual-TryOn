"""Windows-friendly human parsing; masks require user review for shape changes."""
import hashlib
import numpy as np
import cv2
from PIL import Image
from .imaging import validate_mask
from .config import CATEGORIES

# mattmdjaga/segformer_b2_clothes class IDs (not generic COCO labels).
LABELS = {"upper": [4, 17], "lower": [5, 6, 8], "overall": [4, 5, 6, 7, 8, 17]}
PROTECTED = [1, 2, 3, 9, 10, 11, 14, 15]  # head, shoes, exposed arms/hands


def long_dress_envelope(labels, hem_fraction=.92, flare=.2):
    """User-controlled edit-region proposal, NOT inferred cloth geometry.

    A trapezoid removes the trouser-leg gap and permits a longer/wider target
    skirt. The user must inspect it; hem is a fraction of the entire photo.
    """
    if not .5 <= hem_fraction <= .98 or not 0 <= flare <= .6:
        raise ValueError('Hem must be 0.50..0.98 and flare 0..0.60')
    h, w = labels.shape
    lower = np.isin(labels, [5, 6, 8])
    dress = labels == 7
    upper = labels == 4
    if lower.sum() >= 16:
        ys, xs = np.where(lower)
        waist = int(np.percentile(ys, 8))
        band = lower[waist:min(h, waist + max(5, h//15))]
        _, bx = np.where(band)
    elif dress.sum() >= 16:
        ys, xs = np.where(dress)
        waist = int(ys.min() + .4 * (ys.max() - ys.min()))
        band = dress[waist:min(h, waist + max(5, h//15))]
        _, bx = np.where(band)
    elif upper.sum() >= 16:
        ys, xs = np.where(upper)
        waist = int(np.percentile(ys, 80))
        band = upper[max(0, waist-h//20):waist+1]
        _, bx = np.where(band)
    else:
        raise ValueError('No usable clothing region. Paint a full-dress mask manually.')
    if len(bx) < 2:
        bx = xs
    left, right = np.percentile(bx, [3, 97])
    width = max(10.0, right-left)
    left -= .08*width
    right += .08*width
    bottom = round(hem_fraction * (h-1))
    if bottom <= waist + 10:
        raise ValueError('Hem must lie below the waist. Use a full-body photo and lower the hem.')
    envelope = np.zeros((h, w), dtype=np.uint8)
    polygon = np.array([[max(0, left), waist], [min(w-1, right), waist],
                        [min(w-1, right+flare*width), bottom],
                        [max(0, left-flare*width), bottom]], dtype=np.int32)
    cv2.fillConvexPoly(envelope, polygon, 1)
    return envelope


def mask_from_labels(labels, category, dilation=15, profile='standard', hem_fraction=.92, flare=.2):
    if category not in CATEGORIES:
        raise ValueError(f"Category must be one of {CATEGORIES}")
    if profile not in ('standard', 'long_dress'):
        raise ValueError('Unknown mask profile')
    if profile == 'long_dress' and category != 'overall':
        raise ValueError('Long-dress mask requires the overall category')
    binary = np.isin(labels, LABELS[category]).astype(np.uint8)
    if binary.sum() < 16:
        raise ValueError("Parser could not find this clothing category. Use the manual mask editor.")
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilation | 1, dilation | 1))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    binary = cv2.dilate(binary, kernel)
    if profile == 'long_dress':
        binary |= long_dress_envelope(labels, hem_fraction, flare)
    protected = np.isin(labels, PROTECTED).astype(np.uint8)
    protected = cv2.dilate(protected, np.ones((3, 3), np.uint8))
    binary[protected > 0] = 0
    return validate_mask(Image.fromarray(binary * 255), (labels.shape[1], labels.shape[0]))


class ClothingParser:
    def __init__(self, model_dir):
        self.model_dir = model_dir
        self.model = None
        self._labels_cache = None

    def clear_cache(self):
        self._labels_cache = None

    def load(self):
        if self.model is not None:
            return
        import torch
        from transformers import AutoImageProcessor, AutoModelForSemanticSegmentation
        path = self.model_dir / "parser"
        if not path.exists():
            raise RuntimeError("Parser weights missing. Run python scripts/download_models.py")
        self.processor = AutoImageProcessor.from_pretrained(str(path), local_files_only=True, use_fast=False)
        self.model = AutoModelForSemanticSegmentation.from_pretrained(str(path), local_files_only=True).eval().to("cpu")

    def __call__(self, image, category, profile="standard", hem_fraction=.92, flare=.2):
        import torch
        self.load()
        key = (image.size, hashlib.blake2b(image.tobytes(), digest_size=16).digest())
        if self._labels_cache is not None and self._labels_cache[0] == key:
            labels = self._labels_cache[1]
        else:
            with torch.inference_mode():
                inputs = self.processor(images=image, return_tensors="pt")
                logits = self.model(**inputs).logits
                logits = torch.nn.functional.interpolate(logits, size=(image.height, image.width), mode="bilinear", align_corners=False)
                labels = logits.argmax(dim=1)[0].cpu().numpy()
            # One image only. No disk cache of personal images.
            self._labels_cache = (key, labels)
        mask = mask_from_labels(labels, category, max(9, int(min(image.size)*.025)) | 1,
                                profile=profile, hem_fraction=hem_fraction, flare=flare)
        # Stable, deterministic debug palette.
        palette = np.array([(i*43 % 256, i*97 % 256, i*167 % 256) for i in range(18)], dtype=np.uint8)
        return mask, Image.fromarray(palette[labels])

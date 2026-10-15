"""Garment-reference preparation. Preserve observed cloth; never invent hidden fabric.

This is semantic clothing extraction, NOT foreground/person background removal.
Automatic masks must be reviewed: a human parser is not an instance-aware flat-lay
reconstruction model. Manual masks use the same crop/compositing path.
"""
from dataclasses import dataclass
import cv2
import numpy as np
from PIL import Image


@dataclass
class PreparedGarment:
    image: Image.Image
    mask: Image.Image
    metadata: dict


def cloth_mask(labels, category):
    if category not in ('upper', 'lower', 'overall'):
        raise ValueError('Unsupported garment category')
    labels = np.asarray(labels)
    if labels.ndim != 2:
        raise ValueError('Expected a two-dimensional clothing label map')
    warnings = []
    if category == 'overall':
        # Prefer an actual dress. Do not accidentally cut out the model's trousers.
        if np.count_nonzero(labels == 7) >= 16:
            keep = np.isin(labels, [7])
            # A shirt-dress's tie/panel can be classified as 'upper clothes'.
            # Recover ONLY clothing-labelled islands enclosed by the dress; never
            # fill a skin/hand/background hole or synthesize hidden cloth.
            outside = np.pad((~keep).astype(np.uint8), 1, constant_values=1)
            cv2.floodFill(outside, None, (0, 0), 2)
            enclosed = outside[1:-1, 1:-1] == 1
            keep |= enclosed & np.isin(labels, [4, 5, 8])
        elif np.count_nonzero(labels == 4) >= 16:
            keep = np.isin(labels, [4, 5])
            warnings.append('Parser did not label a dress. Proposed upper/skirt clothing only: verify the ENTIRE dress, sleeves and hem or correct the mask.')
        else:
            raise ValueError('No dress region detected. Paint a garment-only reference mask manually.')
    else:
        keep = np.isin(labels, [4] if category == 'upper' else [5, 6])
    # Include a belt only where it borders this garment, never standalone bags/scarves.
    near = cv2.dilate(keep.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    keep |= (labels == 8) & near
    # NO indiscriminate closing/hole filling or outward dilation into skin/background.
    count, components, stats, _ = cv2.connectedComponentsWithStats(keep.astype(np.uint8), 8)
    retained = np.zeros_like(keep)
    sizes = []
    threshold = max(12, round(labels.size * .0005))
    for index in range(1, count):
        area = int(stats[index, cv2.CC_STAT_AREA])
        if area >= threshold:
            retained |= components == index
            sizes.append(area)
    if len(sizes) > 1 and sorted(sizes, reverse=True)[1] > max(100, .15*max(sizes)):
        warnings.append('Several substantial clothing regions detected. Keep only the intended single garment; remove other people/items manually.')
    if retained.mean() < .01:
        raise ValueError('Too little clothing found. Use a clearer single-garment photo or paint its mask manually.')
    return Image.fromarray(retained.astype(np.uint8)*255), warnings


def prepare_from_mask(image, mask, category, method='manual', warnings=None):
    if category not in ('upper', 'lower', 'overall'):
        raise ValueError('Unsupported garment category')
    if mask.size != image.size:
        raise ValueError('Garment mask must match the original reference photo dimensions')
    binary = np.asarray(mask.convert('L')) > 127
    if binary.sum() < 64 or binary.mean() < .001:
        raise ValueError('Empty / tiny garment selection. Paint the garment, not the person or background.')
    ys, xs = np.where(binary)
    x0, x1, y0, y1 = int(xs.min()), int(xs.max())+1, int(ys.min()), int(ys.max())+1
    if min(x1-x0, y1-y0) < 12:
        raise ValueError('Garment selection is too narrow to use')
    notes = list(warnings or [])
    if binary[0].any() or binary[-1].any() or binary[:, 0].any() or binary[:, -1].any():
        notes.append('Garment touches the photo edge: sleeves/hem may be cropped. Prefer a complete front view.')
    notes.append('Review before use. Skin, hair, face, legs and background should be white; fabric hidden by a pose is NOT reconstructed.')
    normalized = Image.fromarray(binary.astype(np.uint8)*255)
    canvas = Image.new('RGB', image.size, 'white')
    canvas.paste(image.convert('RGB'), (0, 0), normalized)
    crop = canvas.crop((x0, y0, x1, y1))
    # Preserve aspect ratio and margins; no stretching, generative fill or colour change.
    margin = max(8, round(max(crop.size)*.06))
    result = Image.new('RGB', (crop.width+2*margin, crop.height+2*margin), 'white')
    result.paste(crop, (margin, margin))
    result.thumbnail((1536, 1536), Image.Resampling.LANCZOS)
    return PreparedGarment(result, normalized, {'method':method, 'category':category,
        'crop_box':[x0, y0, x1, y1], 'source_size':list(image.size), 'prepared_size':list(result.size),
        'selected_fraction':round(float(binary.mean()), 4), 'warnings':notes,
        'review_required':True, 'hidden_fabric_reconstructed':False})

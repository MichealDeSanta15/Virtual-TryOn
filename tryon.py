"""
Try-on engine interface.
To be implemented by Friend 3 with Stable Diffusion / ControlNet warping.
"""
from typing import Optional
import numpy as np


def try_on_garment(frame: np.ndarray, garment_path: str) -> Optional[np.ndarray]:
    """
    Run AI try-on overlay on the video frame.
    Returns None by default so mock_services falls back to the mock overlay.
    """
    return None

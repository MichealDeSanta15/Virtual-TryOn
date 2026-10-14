"""Member 1 compatibility API. Calls block: invoke from an AI worker, not Qt's UI thread."""
import threading
from edgeai.engine import TryOnEngine
_engine = None
_lock = threading.Lock()

def get_engine():
    global _engine
    with _lock:
        if _engine is None:
            _engine = TryOnEngine()
    return _engine

def try_on_garment(frame, garment_path, category="upper", **kwargs):
    return get_engine().try_on_garment(frame, garment_path, category, **kwargs)

def generate_tryon(frame, garment_paths, category="upper", **kwargs):
    return get_engine().generate_tryon(frame, garment_paths, category, **kwargs)

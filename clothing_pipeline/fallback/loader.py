"""No generated product placeholders. Import your own licensed photos into the catalog.

The old class name is retained for compatibility, but an empty catalog stays empty.
"""
class FallbackDataset:
    def get_all(self): return []
    def search(self, **kwargs): return []

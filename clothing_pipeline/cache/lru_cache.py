"""Missing upstream component: persistent ID cache with fixed TTL and bounded LRU."""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from clothing_pipeline.config import CACHE_MAX_ENTRIES, CACHE_TTL_HOURS


class QueryCache:
    def __init__(self, db, max_entries=CACHE_MAX_ENTRIES, ttl_hours=CACHE_TTL_HOURS):
        self.db, self.max_entries, self.ttl = db, max_entries, timedelta(hours=ttl_hours)

    @staticmethod
    def key(params):
        return hashlib.sha256(json.dumps(params, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def get(self, params):
        key = self.key(params)
        entry = self.db.get_cache_entry(key)
        if entry is None:
            return None
        created = datetime.fromisoformat(entry['created_at']).replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc)-created > self.ttl:
            self.db.delete_cache_entry(key)
            return None
        return entry['result_ids']

    def put(self, params, ids):
        self.db.set_cache_entry(self.key(params), ids)
        self.db.evict_lru_cache(self.max_entries)

    def clear(self):
        self.db.clear_cache()

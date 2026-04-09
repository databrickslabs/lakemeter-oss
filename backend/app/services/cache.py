"""In-memory TTL cache for Lakebase reference data."""
import threading
import hashlib
import json
from cachetools import TTLCache


class ReferenceDataCache:
    """Thread-safe TTL cache for reference data from Lakebase."""

    def __init__(self, maxsize: int = 512, ttl: int = 3600):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.Lock()

    def _make_key(self, prefix: str, **kwargs) -> str:
        params_str = json.dumps(kwargs, sort_keys=True, default=str)
        return f"{prefix}:{hashlib.md5(params_str.encode()).hexdigest()}"

    def get(self, prefix: str, **kwargs):
        key = self._make_key(prefix, **kwargs)
        with self._lock:
            return self._cache.get(key)

    def set(self, prefix: str, value, **kwargs):
        key = self._make_key(prefix, **kwargs)
        with self._lock:
            self._cache[key] = value

    def invalidate(self, prefix: str, **kwargs):
        key = self._make_key(prefix, **kwargs)
        with self._lock:
            self._cache.pop(key, None)

    def clear(self):
        with self._lock:
            self._cache.clear()


# Singleton instance — 1-hour TTL for reference data
ref_cache = ReferenceDataCache(maxsize=512, ttl=3600)

import time
from typing import Dict, Any, Optional

class WebCache:
    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {} # URL -> {data, expiry}

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        if url in self._cache:
            entry = self._cache[url]
            if entry["expiry"] > time.time():
                return entry["data"]
            else:
                # Expired
                del self._cache[url]
        return None

    def set(self, url: str, data: Dict[str, Any], ttl: Optional[int] = None):
        expiry_ttl = ttl if ttl is not None else self.default_ttl
        self._cache[url] = {
            "data": data,
            "expiry": time.time() + expiry_ttl
        }

    def clear(self):
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        now = time.time()
        active = sum(1 for entry in self._cache.values() if entry["expiry"] > now)
        return {
            "cache_size": len(self._cache),
            "active_entries": active,
            "expired_entries": len(self._cache) - active
        }

global_web_cache = WebCache()

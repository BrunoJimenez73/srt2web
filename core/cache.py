# File: core/cache.py
import time
from collections import OrderedDict
from typing import Any, Optional


class LRUCache:
    """LRU cache con TTL (Time To Live)"""

    def __init__(self, maxsize: int = 500, ttl_seconds: int = 60):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[Any, tuple[Any, float]] = OrderedDict()

    def get(self, key: Any) -> Optional[Any]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                # Move to end (LRU)
                self.cache.move_to_end(key)
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key: Any, value: Any) -> None:
        if key in self.cache:
            del self.cache[key]
        elif len(self.cache) >= self.maxsize:
            # Remove oldest (first item in OrderedDict)
            self.cache.popitem(last=False)

        self.cache[key] = (value, time.time())

    def clear(self) -> None:
        self.cache.clear()


# Tests mínimos:
if __name__ == "__main__":
    cache = LRUCache(maxsize=3, ttl_seconds=1)
    cache.set("a", 1)
    assert cache.get("a") == 1
    print("✓ LRUCache básico funciona")

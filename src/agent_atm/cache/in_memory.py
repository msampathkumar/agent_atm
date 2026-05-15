from datetime import datetime, timedelta
import threading
from typing import Any, Dict, Optional, Tuple
from agent_atm.cache.base import BaseStore

class InMemoryCacheStore(BaseStore):
    """Thread-safe in-memory cache store with TTL validation."""
    
    def __init__(self):
        self._cache: Dict[str, Tuple[Any, Optional[datetime]]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            val, expires_at = self._cache[key]
            if expires_at and datetime.now() > expires_at:
                del self._cache[key]
                return None
            return val

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires_at = None
        if ttl is not None:
            expires_at = datetime.now() + timedelta(seconds=ttl)
        with self._lock:
            self._cache[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

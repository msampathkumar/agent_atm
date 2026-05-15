from typing import Dict, Type
from agent_atm.cache.base import BaseStore
from agent_atm.cache.disk import DiskCacheStore
from agent_atm.cache.in_memory import InMemoryCacheStore

_REGISTRY: Dict[str, Type[BaseStore]] = {
    "disk": DiskCacheStore,
    "memory": InMemoryCacheStore
}

def get_store(driver: str = "disk", **kwargs) -> BaseStore:
    """Factory loader for cache stores based on Swappable Component Architecture."""
    if driver not in _REGISTRY:
        raise ValueError(f"Unknown cache driver shorthand: '{driver}'. Supported: {list(_REGISTRY.keys())}")
    return _REGISTRY[driver](**kwargs)

# Expose default virtual store instance
FastStore: BaseStore = get_store("disk")

__all__ = ["BaseStore", "DiskCacheStore", "InMemoryCacheStore", "get_store", "FastStore"]

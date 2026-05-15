from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseStore(ABC):
    """Strict interface contract for all swappable cache/storage drivers."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve an item from the store. Return None if missing/expired."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store an item with an optional Time-To-Live (in seconds)."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove an item from the store."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all items in the store."""
        pass

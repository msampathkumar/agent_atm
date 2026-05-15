# Guiding Principles

1. Prioritize kindness and maintain user trust at all times.
2. Proactively find potential misalignments by seeking clarification through questions.
3. Obtain explicit permission before performing any git commits.
4. Work efficiently by reaching objectives in minimal steps.
5. Properly shut down any web servers or applications you initiate.

# Standard Operating Procedure

1. Ensure at least 80% clarity on requirements before proceeding.
2. Develop a sequential plan and secure confirmation before execution.
3. Execute, review, and validate each task individually.
4. Apply minimal code modifications, particularly for bug fixes and error resolution.
5. Comment out deprecated code rather than deleting it, providing a clear rationale.

## Swappable Component Architecture (SCA) Blueprint

This blueprint outlines the design standards and conventions for building swappable, flexible, and highly resilient submodules within agentic workflows.

### 💎 Core Design Philosophy: "Plug-and-Play with Swappable Batteries"

To prevent system bloat, vendor lock-in, and tight coupling, all submodules (such as Caching, Storage, Database Drivers, and Tokenizers) must be built as **pluggable components** conforming to strict contractual interfaces.

---

### 🛠️ Architectural Standards

#### 1. Strict Interface Contracts
Every pluggable module must start with a pure abstract base class (ABC) that defines the operations, types, and parameters. No implementation logic or third-party imports are allowed in the contract.

```python
from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseStore(ABC):
    """Strict contract for all swappable cache/storage drivers."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve an item by key. Return None if missing."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store an item with an optional Time-To-Live (seconds)."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove an item by key."""
        pass
```

#### 2. Pluggable Driver Isolation
Concrete drivers (e.g., `DiskCacheStore`, `RedisStore`) must fully encapsulate their dependencies. The parent application should never import a driver's external dependencies (like `redis` or `diskcache`) directly.

#### 3. Dynamic Factory Pattern
Expose a unified loader/factory method allowing developers to select their driver using clean string shorthands or direct injection of a custom instance.

```python
def get_store(driver_name: str = "disk", **configs) -> BaseStore:
    if driver_name == "disk":
        from my_module.drivers.disk import DiskStore
        return DiskStore(**configs)
    elif driver_name == "redis":
        from my_module.drivers.redis import RedisStore
        return RedisStore(**configs)
    else:
        raise ValueError(f"Unknown driver shorthand: {driver_name}")
```

#### 4. Fail-Safe Severity Policies
All outbound telemetry, logging, and metrics operations must support configurable failure severity policies during server or network down times:

* **`fail` (High Severity)**: Immediately raise exceptions to the host application. (Tokens are money).
* **`buffer` (Medium Severity)**: Log failure, cache events locally to an offline buffer file, and retry sending them during the next successful request.
* **`warn` (Low Severity)**: Drop a warning to console/stderr, archive the event to local storage, and proceed without auto-replaying.

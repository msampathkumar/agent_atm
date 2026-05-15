from typing import Union
from agent_atm.data_managers.base import BaseDataManager

def get_data_manager(name: Union[str, BaseDataManager] = "in_memory", **kwargs) -> BaseDataManager:
    """Dynamic factory loader for data managers conforming to Swappable Component Architecture (SCA)."""
    if not isinstance(name, str):
        return name

    if name == "in_memory":
        from agent_atm.data_managers.in_memory import InMemoryManager
        # InMemoryManager takes no args, clean out database-specific parameters
        cleaned = {k: v for k, v in kwargs.items() if k not in ("db_url", "db_path")}
        return InMemoryManager(**cleaned)
    elif name == "sqlite":
        from agent_atm.data_managers.sqlalchemy import SQLAlchemyManager
        db_path = kwargs.get("db_path") or kwargs.get("db_url") or "agent_atm.db"
        return SQLAlchemyManager(db_url=db_path)
    elif name == "remote":
        from agent_atm.client import RemoteHTTPDataManager
        base_url = kwargs.get("base_url") or "http://127.0.0.1:8000"
        return RemoteHTTPDataManager(base_url=base_url)
    else:
        raise ValueError(f"Unknown database manager shorthand: '{name}'")

__all__ = [
    "BaseDataManager",
    "get_data_manager"
]

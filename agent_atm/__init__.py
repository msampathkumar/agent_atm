from typing import Any, List, Optional, Union

from agent_atm.context import TokenEvent, context
from agent_atm.data_managers.base import BaseDataManager
from agent_atm.types import Scope, Quota, AlertLevel
from agent_atm.limits import TokenQuotaExceeded
from agent_atm.core import AgentTokenManager


# Global default manager instance
_global_manager: Optional[AgentTokenManager] = None

def init(
    data_manager: Union[str, BaseDataManager] = "in_memory",
    async_write: bool = False,
    db_path: str = "agent_atm.db",
    default_app_id: Optional[str] = None,
    tokenizer: Optional[Any] = None
) -> AgentTokenManager:
    """Initialize the global singleton instance of AgentTokenManager.
    
    Example:
        import agent_atm as atm
        atm.init(data_manager="sqlite", db_path="usage.db")
    """
    global _global_manager
    _global_manager = AgentTokenManager(
        data_manager=data_manager,
        async_write=async_write,
        db_path=db_path,
        default_app_id=default_app_id,
        tokenizer=tokenizer
    )
    return _global_manager


def _get_manager() -> AgentTokenManager:
    global _global_manager
    if _global_manager is None:
        # Automatically initialize default in-memory manager if not explicitly initialized
        _global_manager = AgentTokenManager(data_manager="in_memory")
    return _global_manager

def add_user_request(
    content: Any = None, 
    token_count: Optional[int] = None,
    model_id: str = "default",
    username: Optional[str] = None,
    session_id: Optional[str] = None,
    app_id: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> TokenEvent:
    """Record a user request event using the global manager."""
    return _get_manager().add_user_request(
        content, token_count, model_id, username, session_id, app_id, tags
    )

def add_model_response(
    content: Any = None, 
    token_count: Optional[int] = None,
    model_id: str = "default",
    username: Optional[str] = None,
    session_id: Optional[str] = None,
    app_id: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> TokenEvent:
    """Record a model response event using the global manager."""
    return _get_manager().add_model_response(
        content, token_count, model_id, username, session_id, app_id, tags
    )

# Expose limits registration proxies
class LimitsProxy:
    def add(self, scope: Scope, quota: Quota, alert_level: AlertLevel = AlertLevel.BLOCKING) -> None:
        """Register a token limit rule on the global manager."""
        _get_manager().limits.add(scope=scope, quota=quota, alert_level=alert_level)

limits = LimitsProxy()

# Expose hooks registration proxies
def hook(hook_type: str):
    """Decorator to register a validation or callback hook on the global manager.
    
    Example:
        @atm.hook("pre")
        def check_something(event):
            ...
    """
    return _get_manager().hooks.register(hook_type)

def add_hook(func, hook_type: str = "pre") -> None:
    """Register a hook function imperatively on the global manager."""
    _get_manager().hooks.add_hook(func, hook_type)

def shutdown() -> None:
    """Gracefully shut down the global manager."""
    global _global_manager
    if _global_manager is not None:
        _global_manager.shutdown()

__all__ = [
    "AgentTokenManager",
    "TokenEvent",
    "context",
    "init",
    "add_user_request",
    "add_model_response",
    "Scope",
    "Quota",
    "AlertLevel",
    "TokenQuotaExceeded",
    "limits",
    "hook",
    "add_hook",
    "shutdown"
]

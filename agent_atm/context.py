"""Module Purpose: Implements the contextual scoping mechanism for LLM request metadata.

Module Function: Manages thread-local and async-local context states, merging metadata variables automatically.
"""

import contextlib
from contextvars import ContextVar
from dataclasses import field
from datetime import datetime
import socket
from typing import Any, Dict, List, Optional

# ==============================================================================
# DEPRECATED: TokenEvent class has been moved to agent_atm/types/event.py.
# Rationale: Modularized types folder holds all core data structure dataclasses.
# ==============================================================================
# @dataclass
# class TokenEvent:
#     timestamp: datetime
#     event_type: str
#     token_count: int
#     model_id: str
#     username: Optional[str] = None
#     session_id: Optional[str] = None
#     app_id: Optional[str] = None
#     hostname: Optional[str] = field(default_factory=socket.gethostname)
#     _additional_metadata_tags: List[str] = field(default_factory=list)
#     _additional_metadata_config: Dict[str, str] = field(default_factory=dict)

from agent_atm.types import TokenEvent

# Context variable for scoping metadata
_context_vars: ContextVar[Dict[str, Any]] = ContextVar("atm_context", default={})

@contextlib.contextmanager
def context(**kwargs):
    """Context manager to enrich events with metadata parameters within a code block.
    
    Any keyword argument that is not a built-in field is automatically placed 
    inside `_additional_metadata_config` as a key-value string pair.
    
    Example:
        with atm.context(session_id="session-123", app_id="my-app", department="marketing", tier="vip"):
            atm.add_user_request("hello")
    """
    current = _context_vars.get()
    
    # Initialize new context dict with copies of lists/dicts to ensure nested-safety
    new_context = {}
    for k, v in current.items():
        if k == "_additional_metadata_config":
            new_context[k] = dict(v)
        elif k == "_additional_metadata_tags":
            new_context[k] = list(v)
        else:
            new_context[k] = v
            
    built_ins = {"username", "session_id", "app_id", "_additional_metadata_tags", "_additional_metadata_config"}
    
    new_config = new_context.setdefault("_additional_metadata_config", {})
    new_tags = new_context.setdefault("_additional_metadata_tags", [])
    
    for k, v in kwargs.items():
        if k in built_ins:
            if k == "_additional_metadata_tags":
                if isinstance(v, list):
                    # Extend or replace depending on preference, let's extend unique tags
                    for tag in v:
                        if tag not in new_tags:
                            new_tags.append(str(tag))
            elif k == "_additional_metadata_config":
                if isinstance(v, dict):
                    new_config.update({str(ki): str(vi) for ki, vi in v.items()})
            else:
                new_context[k] = v
        else:
            # Custom metadata arguments are cast to strings and added to additional_metadata_config
            new_config[k] = str(v)
            
    token = _context_vars.set(new_context)
    try:
        yield
    finally:
        _context_vars.reset(token)

def get_current_context() -> Dict[str, Any]:
    """Retrieve the current active context dictionary."""
    return _context_vars.get()

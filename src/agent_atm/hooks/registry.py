"""Module Purpose: Implements the callback and validator Hook registration system.

Module Function: Executes Pre-Hooks (blocking validation) and Post-Hooks (non-blocking reporting) around logging events.
"""

from typing import Callable, List
import sys
from agent_atm.types import TokenEvent

class HookRegistry:
    """Manages custom Pre-Hooks and Post-Hooks execution list."""
    
    def __init__(self):
        self.pre_hooks: List[Callable[[TokenEvent], None]] = []
        self.post_hooks: List[Callable[[TokenEvent], None]] = []

    def register(self, hook_type: str) -> Callable[[Callable[[TokenEvent], None]], Callable[[TokenEvent], None]]:
        """Decorator interface to register a hook."""
        def decorator(func: Callable[[TokenEvent], None]) -> Callable[[TokenEvent], None]:
            if hook_type == "pre":
                self.pre_hooks.append(func)
            elif hook_type == "post":
                self.post_hooks.append(func)
            else:
                raise ValueError(f"Invalid hook type: {hook_type}. Must be 'pre' or 'post'.")
            return func
        return decorator

    def add_hook(self, func: Callable[[TokenEvent], None], hook_type: str = "pre") -> None:
        """Register a hook function imperatively."""
        if hook_type == "pre":
            self.pre_hooks.append(func)
        elif hook_type == "post":
            self.post_hooks.append(func)
        else:
            raise ValueError(f"Invalid hook type: {hook_type}. Must be 'pre' or 'post'.")

    def trigger_pre_hooks(self, event: TokenEvent) -> None:
        """Execute all registered pre-hooks. Any exception raised will abort the write operation."""
        for hook in self.pre_hooks:
            hook(event)

    def trigger_post_hooks(self, event: TokenEvent) -> None:
        """Execute all registered post-hooks in a safe, non-blocking try-except wrapper."""
        for hook in self.post_hooks:
            try:
                hook(event)
            except Exception as e:
                print(f"[agent-atm] Error running post-hook: {e}", file=sys.stderr)

# ==============================================================================
# DEPRECATED: This module is deprecated and will be removed in version v0.2.0.
# Rationale: Refactored into modular subpackage layout under agent_atm/hooks/.
# ==============================================================================

import warnings
warnings.warn(
    "agent_atm.hooks is deprecated, please use modular agent_atm/hooks package instead.",
    DeprecationWarning,
    stacklevel=2
)

# Forward imports for backward compatibility
from agent_atm.hooks.registry import HookRegistry

__all__ = ["HookRegistry"]

# ==============================================================================
# DEPRECATED: This module is deprecated and will be removed in version v0.2.0.
# Rationale: Refactored into modular layout under agent_atm/types/ and agent_atm/limits/.
# ==============================================================================

import warnings
warnings.warn(
    "agent_atm.limits is deprecated, please import from agent_atm.types or agent_atm.limits package instead.",
    DeprecationWarning,
    stacklevel=2
)

# Forward imports for backward compatibility
from agent_atm.types.limit import AlertLevel, Scope, Quota, LimitRule
from agent_atm.limits.registry import LimitRegistry, TokenQuotaExceeded

__all__ = [
    "AlertLevel",
    "Scope",
    "Quota",
    "LimitRule",
    "LimitRegistry",
    "TokenQuotaExceeded"
]

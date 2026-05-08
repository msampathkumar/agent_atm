"""Module Purpose: Defines the baseline token quota limitation settings and structures.

Module Function: Standardizes target scopes, daily/hourly quotas, and warning/blocking policies.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from agent_atm.types.event import TokenEvent

class AlertLevel(Enum):
    WARNING = "warning"
    BLOCKING = "blocking"

@dataclass
class Scope:
    app: str = "*"
    user: str = "*"
    session: str = "*"

    def matches(self, event: TokenEvent) -> bool:
        """Check if the event metadata matches this limit rule scope."""
        if self.app != "*" and event.app_id != self.app:
            return False
        if self.user != "*" and event.username != self.user:
            return False
        if self.session != "*" and event.session_id != self.session:
            return False
        return True

@dataclass
class Quota:
    total_limit: Optional[int] = None
    day_limit: Optional[int] = None
    hour_limit: Optional[int] = None
    minute_limit: Optional[int] = None

@dataclass
class LimitRule:
    scope: Scope
    quota: Quota
    alert_level: AlertLevel = AlertLevel.BLOCKING

"""Module Purpose: Implements the Token Quota Limits matching and evaluation registry.

Module Function: Analyzes recorded usage over minute, hour, and daily windows to prevent token overflow.
"""

from datetime import datetime, timedelta
import sys
from typing import List
from agent_atm.types import TokenEvent, Scope, Quota, LimitRule, AlertLevel
from agent_atm.data_managers.base import BaseDataManager

class TokenQuotaExceeded(Exception):
    """Raised when a configured token limit has been exceeded."""
    pass

class LimitRegistry:
    """Registry of token limit and quota rules, with validation verification."""
    
    def __init__(self):
        self.rules: List[LimitRule] = []

    def add(self, scope: Scope, quota: Quota, alert_level: AlertLevel = AlertLevel.BLOCKING) -> None:
        """Register a new token limit rule.
        
        Example:
            atm.limits.add(Scope(user="Joe"), Quota(day_limit=50000), AlertLevel.BLOCKING)
        """
        self.rules.append(LimitRule(scope=scope, quota=quota, alert_level=alert_level))

    def validate(self, event: TokenEvent, data_manager: BaseDataManager) -> None:
        """Verify if the new event violates any registered limits.
        
        Raises:
            TokenQuotaExceeded: If a limit is breached and set to AlertLevel.BLOCKING.
        """
        now = datetime.now()
        
        # Check matching rules
        for rule in self.rules:
            if not rule.scope.matches(event):
                continue
            
            quota = rule.quota
            
            # Query filters based on rule scope (if "*" we do not pass the filter to calculate aggregate usage)
            filter_app = event.app_id if rule.scope.app != "*" else None
            filter_user = event.username if rule.scope.user != "*" else None
            filter_session = event.session_id if rule.scope.session != "*" else None
            
            # 1. Total Limit Check
            if quota.total_limit is not None:
                current = data_manager.get_usage(
                    app_id=filter_app,
                    username=filter_user,
                    session_id=filter_session
                )
                if current + event.token_count > quota.total_limit:
                    self._handle_breach(rule, f"Total limit of {quota.total_limit} tokens exceeded.")

            # 2. Day Limit Check (last 24 hours)
            if quota.day_limit is not None:
                start_time = now - timedelta(days=1)
                current = data_manager.get_usage(
                    app_id=filter_app,
                    username=filter_user,
                    session_id=filter_session,
                    start_time=start_time
                )
                if current + event.token_count > quota.day_limit:
                    self._handle_breach(rule, f"Daily limit of {quota.day_limit} tokens exceeded.")

            # 3. Hour Limit Check (last 1 hour)
            if quota.hour_limit is not None:
                start_time = now - timedelta(hours=1)
                current = data_manager.get_usage(
                    app_id=filter_app,
                    username=filter_user,
                    session_id=filter_session,
                    start_time=start_time
                )
                if current + event.token_count > quota.hour_limit:
                    self._handle_breach(rule, f"Hourly limit of {quota.hour_limit} tokens exceeded.")

            # 4. Minute Limit Check (last 1 minute)
            if quota.minute_limit is not None:
                start_time = now - timedelta(minutes=1)
                current = data_manager.get_usage(
                    app_id=filter_app,
                    username=filter_user,
                    session_id=filter_session,
                    start_time=start_time
                )
                if current + event.token_count > quota.minute_limit:
                    self._handle_breach(rule, f"Per-minute limit of {quota.minute_limit} tokens exceeded.")

    def _handle_breach(self, rule: LimitRule, message: str) -> None:
        full_msg = f"[agent-atm] Quota Breach: {message} Scope: app={rule.scope.app}, user={rule.scope.user}, session={rule.scope.session}."
        if rule.alert_level == AlertLevel.BLOCKING:
            raise TokenQuotaExceeded(full_msg)
        else:
            print(f"WARNING: {full_msg}", file=sys.stderr)

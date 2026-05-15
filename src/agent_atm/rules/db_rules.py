from datetime import datetime, timedelta
import sys
from agent_atm.context import TokenEvent
from agent_atm.data_managers.base import BaseDataManager
from agent_atm.rules.exceptions import DBRuleTokenAllowanceExceeded

import logging
logger = logging.getLogger("agent_atm")

class DBRuleEvaluator:
    """Evaluator to check token consumption events against limits registered in database tables."""

    def validate(self, event: TokenEvent, data_manager: BaseDataManager) -> None:
        """Query SQLAlchemy database manager rules table and validate usage metrics."""
        if not hasattr(data_manager, "get_all_rules"):
            return

        rules = data_manager.get_all_rules()
        logger.debug(f"Validating event against DB limit rules: {event.token_count} tokens")
        now = datetime.now()

        for rule in rules:
            # Check scope matching
            match_app = rule["scope_app"] == "*" or rule["scope_app"] == event.app_id
            match_user = rule["scope_user"] == "*" or rule["scope_user"] == event.username
            match_session = rule["scope_session"] == "*" or rule["scope_session"] == event.session_id

            if not (match_app and match_user and match_session):
                continue

            # Filters based on matched scopes
            filter_app = event.app_id if rule["scope_app"] != "*" else None
            filter_user = event.username if rule["scope_user"] != "*" else None
            filter_session = event.session_id if rule["scope_session"] != "*" else None

            if hasattr(data_manager, "get_usage_summary"):
                summary = data_manager.get_usage_summary(
                    app_id=filter_app,
                    username=filter_user,
                    session_id=filter_session
                )
                if rule["total_limit"] is not None and summary["total"] + event.token_count > rule["total_limit"]:
                    self._handle_db_breach(rule, f"Total limit of {rule['total_limit']} tokens exceeded.")
                if rule["day_limit"] is not None and summary["day"] + event.token_count > rule["day_limit"]:
                    self._handle_db_breach(rule, f"Daily limit of {rule['day_limit']} tokens exceeded.")
                if rule["hour_limit"] is not None and summary["hour"] + event.token_count > rule["hour_limit"]:
                    self._handle_db_breach(rule, f"Hourly limit of {rule['hour_limit']} tokens exceeded.")
                if rule["minute_limit"] is not None and summary["minute"] + event.token_count > rule["minute_limit"]:
                    self._handle_db_breach(rule, f"Per-minute limit of {rule['minute_limit']} tokens exceeded.")
            else:
                # 1. Total limit
                if rule["total_limit"] is not None:
                    current = data_manager.get_usage(
                        app_id=filter_app,
                        username=filter_user,
                        session_id=filter_session
                    )
                    if current + event.token_count > rule["total_limit"]:
                        self._handle_db_breach(rule, f"Total limit of {rule['total_limit']} tokens exceeded.")

                # 2. Daily limit
                if rule["day_limit"] is not None:
                    start_time = now - timedelta(days=1)
                    current = data_manager.get_usage(
                        app_id=filter_app,
                        username=filter_user,
                        session_id=filter_session,
                        start_time=start_time
                    )
                    if current + event.token_count > rule["day_limit"]:
                        self._handle_db_breach(rule, f"Daily limit of {rule['day_limit']} tokens exceeded.")

                # 3. Hourly limit
                if rule["hour_limit"] is not None:
                    start_time = now - timedelta(hours=1)
                    current = data_manager.get_usage(
                        app_id=filter_app,
                        username=filter_user,
                        session_id=filter_session,
                        start_time=start_time
                    )
                    if current + event.token_count > rule["hour_limit"]:
                        self._handle_db_breach(rule, f"Hourly limit of {rule['hour_limit']} tokens exceeded.")

                # 4. Per-minute limit
                if rule["minute_limit"] is not None:
                    start_time = now - timedelta(minutes=1)
                    current = data_manager.get_usage(
                        app_id=filter_app,
                        username=filter_user,
                        session_id=filter_session,
                        start_time=start_time
                    )
                    if current + event.token_count > rule["minute_limit"]:
                        self._handle_db_breach(rule, f"Per-minute limit of {rule['minute_limit']} tokens exceeded.")

    def _handle_db_breach(self, rule: dict, message: str) -> None:
        full_msg = (
            f"[agent-atm] DB-RULE-TOKEN-ALLOWANCE Breach: {message} "
            f"Scope: app={rule['scope_app']}, user={rule['scope_user']}, session={rule['scope_session']}."
        )
        logger.warning(full_msg)
        if rule["alert_level"] == "BLOCKING":
            raise DBRuleTokenAllowanceExceeded(full_msg)

import importlib.util
import os
import sys
from typing import Callable, List
from agent_atm.context import TokenEvent
from agent_atm.rules.exceptions import (
    CustomAppPyRuleViolation,
    CustomServerPyRuleViolation,
)

import logging
logger = logging.getLogger("agent_atm")

class PyRuleEvaluator:
    """Evaluator to dynamically register, load, and execute custom Python rules at the app or server level."""

    def __init__(self):
        self.app_rules: List[Callable[[TokenEvent], bool]] = []
        self.server_rules: List[Callable[[TokenEvent], bool]] = []
        # DEPRECATED in v1.0: Dynamic CWD rules.py auto-import has been disabled.
        # Rationale: Implicit magic imports violate explicit design principles and introduce security risks.
        # Developers should explicitly register rules via atm.custom_rules.add_app_rule().
        # self._load_cwd_rules_file()

    # def _load_cwd_rules_file(self) -> None:
    #     """Dynamically imports local rules.py from CWD if present."""
    #     rules_path = os.path.join(os.getcwd(), "rules.py")
    #     if os.path.exists(rules_path):
    #         try:
    #             spec = importlib.util.spec_from_file_location("local_rules", rules_path)
    #             if spec and spec.loader:
    #                 module = importlib.util.module_from_spec(spec)
    #                 spec.loader.exec_module(module)
    #                 if hasattr(module, "validate_request"):
    #                     self.add_app_rule(getattr(module, "validate_request"))
    #         except Exception as e:
    #             print(f"[agent-atm] Warning: Failed to dynamically load CWD rules.py: {e}", file=sys.stderr)

    def add_app_rule(self, func: Callable[[TokenEvent], bool]) -> None:
        logger.info(f"Registering application-level custom Python rule: {func.__name__}")
        self.app_rules.append(func)

    def add_server_rule(self, func: Callable[[TokenEvent], bool]) -> None:
        logger.info(f"Registering server-level custom Python rule: {func.__name__}")
        self.server_rules.append(func)

    def validate_app_rules(self, event: TokenEvent) -> None:
        logger.debug(f"Validating event against custom app rules: {event.token_count} tokens")
        for rule in self.app_rules:
            try:
                res = rule(event)
                if res is False:
                    msg = f"[agent-atm] CUSTOM-APP-PY-RULE: Local validation rule rejected request. Scope: app={event.app_id}, user={event.username}."
                    logger.warning(msg)
                    raise CustomAppPyRuleViolation(msg)
            except CustomAppPyRuleViolation:
                raise
            except Exception as e:
                msg = f"[agent-atm] CUSTOM-APP-PY-RULE: Rule evaluation exception: {e}"
                logger.warning(msg)
                raise CustomAppPyRuleViolation(msg) from e

    def validate_server_rules(self, event: TokenEvent) -> None:
        logger.debug(f"Validating event against custom server rules: {event.token_count} tokens")
        for rule in self.server_rules:
            try:
                res = rule(event)
                if res is False:
                    msg = f"[agent-atm] CUSTOM-SERVER-PY-RULE: Server custom validation rule rejected request. Scope: app={event.app_id}, user={event.username}."
                    logger.warning(msg)
                    raise CustomServerPyRuleViolation(msg)
            except CustomServerPyRuleViolation:
                raise
            except Exception as e:
                msg = f"[agent-atm] CUSTOM-SERVER-PY-RULE: Rule evaluation exception: {e}"
                logger.warning(msg)
                raise CustomServerPyRuleViolation(msg) from e

from typing import Callable
from agent_atm.context import TokenEvent
from agent_atm.data_managers.base import BaseDataManager
from agent_atm.rules.db_rules import DBRuleEvaluator
from agent_atm.rules.py_rules import PyRuleEvaluator

class RuleEngine:
    """Coordinating Orchestrator that aggregates and executes all sub-tier evaluators."""

    def __init__(self):
        self.db_evaluator = DBRuleEvaluator()
        self.py_evaluator = PyRuleEvaluator()

    @property
    def app_rules(self):
        return self.py_evaluator.app_rules

    @property
    def server_rules(self):
        return self.py_evaluator.server_rules

    def add_app_rule(self, func: Callable[[TokenEvent], bool]) -> None:
        """Register a custom application-level local python rule callback."""
        self.py_evaluator.add_app_rule(func)

    def add_server_rule(self, func: Callable[[TokenEvent], bool]) -> None:
        """Register a custom server-level custom python rule callback."""
        self.py_evaluator.add_server_rule(func)

    def validate_app_rules(self, event: TokenEvent) -> None:
        """Run all application-level validation rules."""
        self.py_evaluator.validate_app_rules(event)

    def validate_server_rules(self, event: TokenEvent) -> None:
        """Run all server-level validation rules."""
        self.py_evaluator.validate_server_rules(event)

    def validate_db_rules(self, event: TokenEvent, data_manager: BaseDataManager) -> None:
        """Run all database limit validation rules."""
        self.db_evaluator.validate(event, data_manager)

from agent_atm.limits.registry import TokenQuotaExceeded

class DBRuleTokenAllowanceExceeded(TokenQuotaExceeded):
    """Raised when a DB-configured token limit is breached.

    Triggers the DB-RULE-TOKEN-ALLOWANCE validation failure.
    """
    pass

class CustomServerPyRuleViolation(TokenQuotaExceeded):
    """Raised when a server-level custom python rule validation fails.

    Triggers the CUSTOM-SERVER-PY-RULE validation failure.
    """
    pass

class CustomAppPyRuleViolation(TokenQuotaExceeded):
    """Raised when an application-level custom python rule validation fails.

    Triggers the CUSTOM-APP-PY-RULE validation failure.
    """
    pass

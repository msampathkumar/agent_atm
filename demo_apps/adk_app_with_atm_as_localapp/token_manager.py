import agent_atm as atm

def init_atm():
    # Initialize local SQLite persistent database with memory quota caching
    atm.init(data_manager="sqlite", db_path="app_usage.db", default_app_id="adk-local-bot", quota_cache="memory")
    # Register a minute limit rule: 500 tokens max per minute
    atm.limits.add(
        scope=atm.Scope(app="adk-local-bot"),
        quota=atm.Quota(minute_limit=500),
        alert_level=atm.AlertLevel.BLOCKING
    )
    print("--> [token_manager] ATM initialized successfully with SQLite & Quota Caching.")

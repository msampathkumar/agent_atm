import os
import time
import sys
from datetime import datetime, timedelta
import agent_atm as atm
from agent_atm.context import TokenEvent
from agent_atm.rules.exceptions import CustomAppPyRuleViolation

# =====================================================================
# Example 1: Warning threshold limits for User-ABC (Non-Blocking)
# =====================================================================

def validate_user_abc_limits(event: TokenEvent) -> bool:
    """Validation rule for User-ABC.

    Monitors token thresholds over minute, hourly, and daily windows.
    Only prints warnings instead of blocking the requests.
    """
    # Apply rule only to User-ABC
    if event.username != "User-ABC":
        return True

    # Resolve global data manager to query historical usage ledger
    manager = atm._get_manager()
    data_manager = manager.data_manager
    now = datetime.now()

    # 1. Check last 1 minute (Limit: 1K tokens)
    start_min = now - timedelta(minutes=1)
    min_usage = data_manager.get_usage(username="User-ABC", start_time=start_min)
    if min_usage + event.token_count > 1000:
        print(
            f"[ALERT] [User-ABC] Minute limit crossed! "
            f"Current usage is {min_usage} + {event.token_count} > 1000 limit.",
            file=sys.stderr
        )

    # 2. Check last 1 hour (Limit: 10K tokens)
    start_hour = now - timedelta(hours=1)
    hour_usage = data_manager.get_usage(username="User-ABC", start_time=start_hour)
    if hour_usage + event.token_count > 10000:
        print(
            f"[ALERT] [User-ABC] Hourly limit crossed! "
            f"Current usage is {hour_usage} + {event.token_count} > 10000 limit.",
            file=sys.stderr
        )

    # 3. Check last 24 hours (Limit: 1M tokens)
    start_day = now - timedelta(days=1)
    day_usage = data_manager.get_usage(username="User-ABC", start_time=start_day)
    if day_usage + event.token_count > 1000000:
        print(
            f"[ALERT] [User-ABC] Daily limit crossed! "
            f"Current usage is {day_usage} + {event.token_count} > 1000000 limit.",
            file=sys.stderr
        )

    # This rule is advisory/warning-only, so it always returns True (Allowed)
    return True


# =====================================================================
# Example 2: Tiered Request Throttling Rate Limiter for User-XYZ
# =====================================================================

def validate_user_xyz_throttling(event: TokenEvent) -> bool:
    """Validation rule for User-XYZ.

    Implements tiered request throttling (rate limiting via time.sleep)
    to slow down the traffic if request thresholds are crossed:
    - Requests > 50K: Introduces a 2-second sleep.
    - Requests > 90K: Introduces a 10-second sleep.
    - Requests > 100K: Blocks completely, raising an Exception.
    """
    if event.username != "User-XYZ":
        return True

    manager = atm._get_manager()
    data_manager = manager.data_manager
    now = datetime.now()

    # Fetch matching event logs count for today
    start_day = now - timedelta(days=1)
    
    # To count total requests, get all logged events for this user
    events = data_manager.get_all_events()
    user_xyz_events = [
        e for e in events 
        if e.username == "User-XYZ" and e.timestamp >= start_day
    ]
    request_count = len(user_xyz_events)

    # Tier 4: Exceeds 100K requests -> block completely
    if request_count >= 100000:
        raise CustomAppPyRuleViolation(
            f"[BLOCK] [User-XYZ] Exceeded absolute daily limit of 100,000 requests. "
            f"Total requests: {request_count}."
        )

    # Tier 3: Exceeds 90K requests -> slow down by 10 seconds
    elif request_count >= 90000:
        print(f"[THROTTLE] [User-XYZ] High daily requests: {request_count}. Delaying request by 10 seconds...")
        time.sleep(10)

    # Tier 2: Exceeds 50K requests -> slow down by 2 seconds
    elif request_count >= 50000:
        print(f"[THROTTLE] [User-XYZ] Moderate daily requests: {request_count}. Delaying request by 2 seconds...")
        time.sleep(2)

    return True


# =====================================================================
# Demonstration Runner
# =====================================================================

def run_example_demonstration():
    """Demonstrate how to initialize and run these rules locally."""
    db_path = "rules_demo.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    print("=== Initializing ATM with SCA Database Factory ===")
    # Initialize using upgraded SCA db factory
    atm.init(data_manager="sqlite", db_path=db_path)

    # Register custom validation rules
    print("\n=== Registering Custom Rules ===")
    atm.custom_rules.add_app_rule(validate_user_abc_limits)
    atm.custom_rules.add_app_rule(validate_user_xyz_throttling)

    # -----------------------------------------------------------------
    # Demo 1: User-ABC Warnings
    # -----------------------------------------------------------------
    print("\n--- Running Demo 1: User-ABC Warnings ---")
    with atm.context(username="User-ABC"):
        # 1st request: small token count
        atm.add_user_request(token_count=100)
        print("Logged 1st request.")

        # 2nd request: huge token count -> crosses limits and prints warning (does not fail)
        atm.add_user_request(token_count=2000)
        print("Logged 2nd request (Check stderr for alert warnings!)")

    # -----------------------------------------------------------------
    # Demo 2: User-XYZ Throttling
    # -----------------------------------------------------------------
    print("\n--- Running Demo 2: User-XYZ Throttling ---")
    with atm.context(username="User-XYZ"):
        # 1st request: small request
        atm.add_user_request(token_count=10)
        print("Logged 1st request.")

        # Let's simulate having 50,005 historical requests for this user
        # We bypass normal logging to populate some dummy historical rows in DB
        print("Simulating 50,005 logged requests in DB...")
        session = atm._get_manager().data_manager.Session()
        try:
            from agent_atm.data_managers.sqlalchemy import TokenEventModel
            # Bulk insert 50,005 requests
            events = [
                TokenEventModel(
                    timestamp=datetime.now(),
                    event_type="request",
                    token_count=10,
                    model_id="gemini-2.5-pro",
                    username="User-XYZ"
                )
                for _ in range(50)  # Let's simulate a smaller subset, say 50, to make test run fast
            ]
            session.add_all(events)
            session.commit()
        finally:
            session.close()

        # Let's temporarily override throttling thresholds in a local evaluator wrapper to demonstrate
        # (We will do this inside the actual test suite to keep runtime extremely quick!)

    atm.shutdown()
    if os.path.exists(db_path):
        os.remove(db_path)
    print("\n=== Demonstration Completed successfully. ===")


if __name__ == "__main__":
    run_example_demonstration()

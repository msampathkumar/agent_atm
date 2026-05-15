import os
import sys
import time
import pytest
from datetime import datetime
import agent_atm as atm
from agent_atm.context import TokenEvent
from agent_atm.rules.exceptions import (
    DBRuleTokenAllowanceExceeded,
    CustomAppPyRuleViolation,
    CustomServerPyRuleViolation,
)
from agent_atm.cache import FastStore, get_store

def test_faststore_caching():
    """Verify FastStore cache gets, sets, expirations, and deletes work correctly."""
    # Get a fresh disk cache
    cache = get_store("disk", db_path=".test_cache_file.db")
    cache.clear()

    # Set value
    cache.set("my_key", {"tokens": 100}, ttl=2)
    assert cache.get("my_key") == {"tokens": 100}

    # Check delete
    cache.delete("my_key")
    assert cache.get("my_key") is None

    # Check TTL expiration
    cache.set("temp_key", "test_val", ttl=1)
    assert cache.get("temp_key") == "test_val"
    time.sleep(1.2)
    assert cache.get("temp_key") is None

    # Clean up test DB file
    if os.path.exists(".test_cache_file.db"):
        os.remove(".test_cache_file.db")


def test_app_level_validation_rules():
    """Verify application-level custom rules raise CustomAppPyRuleViolation."""
    # Initialize manager
    manager = atm.init(data_manager="in_memory", telemetry_failure_policy="fail")
    manager.rule_engine.app_rules.clear()

    # Register custom app rule function
    def reject_high_tokens(event: TokenEvent) -> bool:
        if event.token_count > 1000:
            return False
        return True

    atm.custom_rules.add_app_rule(reject_high_tokens)

    # This should pass
    atm.add_user_request(token_count=100)

    # This should raise CustomAppPyRuleViolation
    with pytest.raises(CustomAppPyRuleViolation):
        atm.add_user_request(token_count=2000)


def test_db_level_rules_sqlalchemy():
    """Verify DB-level limit rules raise DBRuleTokenAllowanceExceeded."""
    # Initialize with SQLite SQLAlchemy manager
    db_file = "test_rules_db.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    manager = atm.init(data_manager="sqlite", db_path=db_file)
    
    # Clear past rules
    manager.data_manager.clear_all_rules()

    # Register a DB rule: user free-tier is capped to 100 total tokens
    manager.data_manager.register_rule(
        scope_user="free-tier",
        total_limit=100,
        alert_level="BLOCKING"
    )

    # Log some requests within the limit
    with atm.context(username="free-tier"):
        atm.add_user_request(token_count=40)
        atm.add_user_request(token_count=40)

        # Next one exceeds 100 total limit -> raises DBRuleTokenAllowanceExceeded
        with pytest.raises(DBRuleTokenAllowanceExceeded):
            atm.add_user_request(token_count=30)

    # Cleanup
    atm.shutdown()
    if os.path.exists(db_file):
        os.remove(db_file)


def test_telemetry_failure_severity_policies():
    """Verify severity failure policies fail, warn, and buffer correctly."""
    buffer_path = ".agent_atm_failed_events.jsonl"
    if os.path.exists(buffer_path):
        os.remove(buffer_path)

    # 1. Test policy: "fail"
    manager = atm.init(data_manager="in_memory", telemetry_failure_policy="fail")
    # Break data manager save systematically to simulate failure
    def bad_save(event):
        raise ConnectionError("Server unreachable")
    manager.data_manager.save = bad_save

    with pytest.raises(ConnectionError):
        atm.add_user_request(token_count=100)

    # 2. Test policy: "warn"
    manager = atm.init(data_manager="in_memory", telemetry_failure_policy="warn")
    manager.data_manager.save = bad_save

    # Should not raise exception, should log to buffer file
    atm.add_user_request(token_count=150)
    assert os.path.exists(buffer_path)
    os.remove(buffer_path)

    # 3. Test policy: "buffer" (Offline buffering and automatic replay)
    manager = atm.init(data_manager="in_memory", telemetry_failure_policy="buffer")
    manager.data_manager.save = bad_save

    # Telemetry fails -> event is buffered
    atm.add_user_request(token_count=200)
    assert os.path.exists(buffer_path)

    # Fix the database connection
    saved_events = []
    def good_save(event):
        saved_events.append(event)
    manager.data_manager.save = good_save

    # Next request triggers replay -> buffer file is read, successfully drained & deleted
    atm.add_user_request(token_count=50)
    assert not os.path.exists(buffer_path)
    
    # Verify both events (the buffered one and the new one) are saved
    assert len(saved_events) == 2
    assert saved_events[0].token_count == 200
    assert saved_events[1].token_count == 50


def test_data_manager_sca_factory():
    """Verify dynamic SCA factory correctly loads standard data manager drivers."""
    from agent_atm.data_managers import get_data_manager
    from agent_atm.data_managers.in_memory import InMemoryManager
    from agent_atm.data_managers.sqlalchemy import SQLAlchemyManager

    # in_memory
    mgr_mem = get_data_manager("in_memory")
    assert isinstance(mgr_mem, InMemoryManager)

    # sqlite (upgraded SQLAlchemy manager)
    mgr_sql = get_data_manager("sqlite", db_path="sqlite:///:memory:")
    assert isinstance(mgr_sql, SQLAlchemyManager)


def test_segregated_rule_engine():
    """Verify coordinating RuleEngine orchestrates segregated evaluator submodules."""
    from agent_atm.rules.engine import RuleEngine
    from agent_atm.rules.db_rules import DBRuleEvaluator
    from agent_atm.rules.py_rules import PyRuleEvaluator

    engine = RuleEngine()
    assert isinstance(engine.db_evaluator, DBRuleEvaluator)
    assert isinstance(engine.py_evaluator, PyRuleEvaluator)


def test_tiered_throttling_rate_limiter():
    """Verify custom tiered python throttling rule slows down execution correctly."""
    import time
    from agent_atm.rules.exceptions import CustomAppPyRuleViolation

    # Local throttling rule
    def sample_throttling_rule(event: TokenEvent) -> bool:
        # Simple simulation: throttle user VIP-XYZ based on metadata config trigger
        if event.username == "VIP-XYZ":
            mode = event._additional_metadata_config.get("throttle_mode")
            if mode == "2s":
                time.sleep(2)
            elif mode == "10s":
                time.sleep(10)
            elif mode == "block":
                raise CustomAppPyRuleViolation("Throttled: blocked completely.")
        return True

    manager = atm.init(data_manager="in_memory")
    manager.rule_engine.app_rules.clear()
    atm.custom_rules.add_app_rule(sample_throttling_rule)

    # Test Tier 1 (No throttling)
    start = time.perf_counter()
    atm.add_user_request(token_count=10)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.5

    # Test Tier 2 (2s delay throttling)
    with atm.context(username="VIP-XYZ", throttle_mode="2s"):
        start = time.perf_counter()
        atm.add_user_request(token_count=10)
        elapsed = time.perf_counter() - start
        assert elapsed >= 1.9

    # Test Tier 4 (blocking)
    with atm.context(username="VIP-XYZ", throttle_mode="block"):
        with pytest.raises(CustomAppPyRuleViolation):
            atm.add_user_request(token_count=10)

    atm.shutdown()


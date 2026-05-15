from datetime import datetime, timedelta
import pytest
from agent_atm.context import TokenEvent
from agent_atm.data_managers.in_memory import InMemoryManager
from agent_atm.types import Scope, Quota, AlertLevel
from agent_atm.limits.registry import LimitRegistry, TokenQuotaExceeded

def test_limits_blocking_quota():
    mgr = InMemoryManager()
    registry = LimitRegistry()
    
    # Add total limit of 1000 tokens for user 'Joe'
    registry.add(
        scope=Scope(user="Joe"),
        quota=Quota(total_limit=1000),
        alert_level=AlertLevel.BLOCKING
    )
    
    ev_good = TokenEvent(
        timestamp=datetime.now(),
        event_type="request",
        token_count=400,
        model_id="test",
        username="Joe"
    )
    
    # Validate (no exception expected)
    registry.validate(ev_good, mgr)
    mgr.save(ev_good)
    
    ev_breach = TokenEvent(
        timestamp=datetime.now(),
        event_type="request",
        token_count=700,
        model_id="test",
        username="Joe"
    )
    
    # Validate should raise TokenQuotaExceeded as 400 + 700 = 1100 > 1000
    with pytest.raises(TokenQuotaExceeded, match="Total limit of 1000 tokens exceeded"):
        registry.validate(ev_breach, mgr)

def test_limits_warning_quota(caplog):
    mgr = InMemoryManager()
    registry = LimitRegistry()
    
    # Add daily limit of 500 tokens with alert_level = WARNING
    registry.add(
        scope=Scope(app="alert-app"),
        quota=Quota(day_limit=500),
        alert_level=AlertLevel.WARNING
    )
    
    ev_save = TokenEvent(
        timestamp=datetime.now(),
        event_type="request",
        token_count=400,
        model_id="test",
        app_id="alert-app"
    )
    mgr.save(ev_save)
    
    ev_breach = TokenEvent(
        timestamp=datetime.now(),
        event_type="request",
        token_count=200,
        model_id="test",
        app_id="alert-app"
    )
    
    # Validate should not raise, but write warning log
    registry.validate(ev_breach, mgr)
    assert "[agent-atm] Quota Breach: Daily limit of 500 tokens exceeded" in caplog.text

def test_limits_minute_quota():
    mgr = InMemoryManager()
    registry = LimitRegistry()
    
    registry.add(
        scope=Scope(app="*"),
        quota=Quota(minute_limit=100),
        alert_level=AlertLevel.BLOCKING
    )
    
    now = datetime.now()
    
    # Event 5 minutes ago (does not affect minute_limit calculation)
    mgr.save(TokenEvent(
        timestamp=now - timedelta(minutes=5),
        event_type="request",
        token_count=80,
        model_id="test"
    ))
    
    # Event 30 seconds ago (affects minute_limit calculation)
    mgr.save(TokenEvent(
        timestamp=now - timedelta(seconds=30),
        event_type="request",
        token_count=40,
        model_id="test"
    ))
    
    ev_new_good = TokenEvent(
        timestamp=now,
        event_type="request",
        token_count=50,
        model_id="test"
    )
    # 40 + 50 = 90 <= 100 (should pass)
    registry.validate(ev_new_good, mgr)
    
    ev_new_bad = TokenEvent(
        timestamp=now,
        event_type="request",
        token_count=70,
        model_id="test"
    )
    # 40 + 70 = 110 > 100 (should fail)
    with pytest.raises(TokenQuotaExceeded, match="Per-minute limit of 100 tokens exceeded"):
        registry.validate(ev_new_bad, mgr)
        
def test_scope_matching():
    scope = Scope(app="my-app", user="Joe")
    
    # Perfectly matching
    assert scope.matches(TokenEvent(datetime.now(), "request", 10, "model", "Joe", "sess", "my-app")) is True
    
    # App mismatch
    assert scope.matches(TokenEvent(datetime.now(), "request", 10, "model", "Joe", "sess", "other-app")) is False
    
    # User mismatch
    assert scope.matches(TokenEvent(datetime.now(), "request", 10, "model", "Bob", "sess", "my-app")) is False
    
    # Wildcard match
    wild_scope = Scope(app="*", user="Joe")
    assert wild_scope.matches(TokenEvent(datetime.now(), "request", 10, "model", "Joe", "sess", "other-app")) is True


def test_minute_rule_exact_user_scenario():
    """Test 1-minute rule for 100 tokens: 50 tokens pass, 150 tokens fail."""
    mgr = InMemoryManager()
    registry = LimitRegistry()

    registry.add(
        scope=Scope(app="*"),
        quota=Quota(minute_limit=100),
        alert_level=AlertLevel.BLOCKING
    )

    now = datetime.now()

    # 1. Check for 50 tokens for pass test
    ev_pass = TokenEvent(
        timestamp=now,
        event_type="request",
        token_count=50,
        model_id="test"
    )
    registry.validate(ev_pass, mgr)
    mgr.save(ev_pass)

    # 2. Check for 150 tokens for fail test
    ev_fail = TokenEvent(
        timestamp=now,
        event_type="request",
        token_count=150,
        model_id="test"
    )
    with pytest.raises(TokenQuotaExceeded, match="Per-minute limit of 100 tokens exceeded"):
        registry.validate(ev_fail, mgr)


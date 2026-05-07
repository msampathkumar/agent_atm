from datetime import datetime, timedelta
import os
from agent_atm.context import TokenEvent
from agent_atm.data_managers.in_memory import InMemoryManager
from agent_atm.data_managers.sqlite import SqliteManager

def test_in_memory_manager():
    mgr = InMemoryManager()
    now = datetime.now()
    
    ev1 = TokenEvent(
        timestamp=now - timedelta(minutes=5),
        event_type="request",
        token_count=100,
        model_id="gemini-flash",
        app_id="test-app",
        username="alice"
    )
    ev2 = TokenEvent(
        timestamp=now,
        event_type="response",
        token_count=150,
        model_id="gemini-flash",
        app_id="test-app",
        username="bob"
    )
    
    mgr.save(ev1)
    mgr.save(ev2)
    
    # Retrieve total usage
    assert mgr.get_usage() == 250
    # Filter by app_id
    assert mgr.get_usage(app_id="test-app") == 250
    # Filter by username
    assert mgr.get_usage(username="alice") == 100
    assert mgr.get_usage(username="bob") == 150
    # Filter by time window
    assert mgr.get_usage(start_time=now - timedelta(minutes=2)) == 150

def test_sqlite_manager(tmp_path):
    db_file = str(tmp_path / "test_atm.db")
    mgr = SqliteManager(db_path=db_file)
    now = datetime.now()
    
    ev1 = TokenEvent(
        timestamp=now - timedelta(minutes=5),
        event_type="request",
        token_count=100,
        model_id="gemini-pro",
        app_id="sqlite-app",
        username="alice",
        _additional_metadata_tags=["t1"],
        _additional_metadata_config={"dept": "HR"}
    )
    
    mgr.save(ev1)
    
    assert mgr.get_usage() == 100
    assert mgr.get_usage(app_id="sqlite-app") == 100
    assert mgr.get_usage(username="bob") == 0
    
    # Verify all events extraction
    all_events = mgr.get_all_events()
    assert len(all_events) == 1
    assert all_events[0].model_id == "gemini-pro"
    assert all_events[0]._additional_metadata_tags == ["t1"]
    assert all_events[0]._additional_metadata_config == {"dept": "HR"}

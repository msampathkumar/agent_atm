import pytest
from agent_atm.context import TokenEvent
from agent_atm.hooks import HookRegistry
from datetime import datetime

def test_hooks_execution():
    registry = HookRegistry()
    
    pre_executed = False
    post_executed = False
    
    @registry.register("pre")
    def my_pre_hook(event: TokenEvent):
        nonlocal pre_executed
        pre_executed = True
        # Mutate event metadata
        event._additional_metadata_tags.append("pre-mutated")
        
    @registry.register("post")
    def my_post_hook(event: TokenEvent):
        nonlocal post_executed
        post_executed = True
        
    ev = TokenEvent(
        timestamp=datetime.now(),
        event_type="request",
        token_count=50,
        model_id="default",
        _additional_metadata_tags=[]
    )
    
    registry.trigger_pre_hooks(ev)
    assert pre_executed is True
    assert "pre-mutated" in ev._additional_metadata_tags
    
    registry.trigger_post_hooks(ev)
    assert post_executed is True

def test_blocking_pre_hook():
    registry = HookRegistry()
    
    @registry.register("pre")
    def blocking_hook(event):
        raise ValueError("Blocked by pre-hook validation")
        
    ev = TokenEvent(
        timestamp=datetime.now(),
        event_type="request",
        token_count=50,
        model_id="default"
    )
    
    with pytest.raises(ValueError, match="Blocked by pre-hook validation"):
        registry.trigger_pre_hooks(ev)

def test_non_blocking_post_hook(caplog):
    registry = HookRegistry()
    
    @registry.register("post")
    def failing_post_hook(event):
        raise RuntimeError("Failed in post-hook!")
        
    ev = TokenEvent(
        timestamp=datetime.now(),
        event_type="request",
        token_count=50,
        model_id="default"
    )
    
    # Triggering post-hook should capture exception and print error, not raise
    registry.trigger_post_hooks(ev)
    assert "Error running post-hook" in caplog.text

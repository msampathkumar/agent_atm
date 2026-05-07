from agent_atm.context import context, get_current_context

def test_context_enrichment():
    # Initially context should be empty
    assert get_current_context() == {}

    # Enter context scope
    with context(app_id="my-app", username="alice"):
        ctx = get_current_context()
        assert ctx["app_id"] == "my-app"
        assert ctx["username"] == "alice"

        # Nested context scope should merge and override
        with context(username="bob", session_id="session-1"):
            nested_ctx = get_current_context()
            assert nested_ctx["app_id"] == "my-app"
            assert nested_ctx["username"] == "bob"
            assert nested_ctx["session_id"] == "session-1"

        # Restored to parent context
        ctx_restored = get_current_context()
        assert ctx_restored["username"] == "alice"
        assert "session_id" not in ctx_restored

    # Restored to empty global context
    assert get_current_context() == {}

def test_context_arbitrary_config_and_tags():
    assert get_current_context() == {}
    
    # Enter context with custom tags and arbitrary key-value pairs
    with context(_additional_metadata_tags=["env:prod", "finance"], department="accounting", level="vip"):
        ctx = get_current_context()
        assert ctx["_additional_metadata_tags"] == ["env:prod", "finance"]
        assert ctx["_additional_metadata_config"] == {"department": "accounting", "level": "vip"}
        
        # Nested context scope extending tags and adding config keys
        with context(_additional_metadata_tags=["dept:fin"], section="audit", level="super-vip"):
            nested_ctx = get_current_context()
            assert nested_ctx["_additional_metadata_tags"] == ["env:prod", "finance", "dept:fin"]
            assert nested_ctx["_additional_metadata_config"] == {
                "department": "accounting", 
                "level": "super-vip", 
                "section": "audit"
            }
            
    assert get_current_context() == {}

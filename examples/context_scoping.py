"""Example: Context Scoping & Metadata Customization

This example showcases how to use atm.context() to isolate and enrich LLM token 
requests with nested tags and custom key-value metadata configuration properties.
"""

import agent_atm as atm

def run_example():
    print("Running Context Scoping Example...")
    
    # Initialize ATM in-memory
    atm.init(data_manager="in_memory", default_app_id="demo-app")

    # 1. Base context scope
    with atm.context(
        username="bob", 
        session_id="session-1", 
        _additional_metadata_tags=["env:prod"],
        department="engineering"
    ):
        # Record request
        ev1 = atm.add_user_request("Hello world!", token_count=5)
        
        # Assert context values mapped correctly
        assert ev1.username == "bob"
        assert ev1.session_id == "session-1"
        assert ev1.app_id == "demo-app"
        assert ev1._additional_metadata_tags == ["env:prod"]
        assert ev1._additional_metadata_config == {"department": "engineering"}

        # 2. Nested context scope extending tags and modifying/adding configs
        with atm.context(
            username="alice", 
            _additional_metadata_tags=["section:auth"],
            role="team-lead",
            department="security"
        ):
            ev2 = atm.add_model_response("Hello back!", token_count=8)
            
            # Assert overrides and nested merging
            assert ev2.username == "alice"  # Overridden
            assert ev2.session_id == "session-1"  # Inherited
            assert ev2._additional_metadata_tags == ["env:prod", "section:auth"]  # Extended
            assert ev2._additional_metadata_config == {
                "department": "security",  # Overridden config
                "role": "team-lead"        # Appended config
            }

        # 3. Parent context remains restored
        ev3 = atm.add_user_request("Parent request", token_count=4)
        assert ev3.username == "bob"
        assert ev3._additional_metadata_tags == ["env:prod"]
        assert ev3._additional_metadata_config == {"department": "engineering"}

    print("Context Scoping Example complete! All assertions passed successfully.")

if __name__ == "__main__":
    run_example()

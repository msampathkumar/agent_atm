"""Example: Pre-Hooks & Post-Hooks Custom Callbacks

This example showcases how to register and execute Pre-Hooks (for blocking validation 
or metadata mutations) and Post-Hooks (for non-blocking reporting or Slack alerting).
"""

import agent_atm as atm

def run_example():
    print("Running Hooks Validation Example...")
    
    atm.init(data_manager="in_memory")

    pre_hook_fired = False
    post_hook_fired = False

    # 1. Register Pre-hook: Executed BEFORE saving. Can mutate event or raise exceptions.
    @atm.hook("pre")
    def validate_and_mutate_event(event):
        nonlocal pre_hook_fired
        pre_hook_fired = True
        
        # Validate mandatory field
        if not event.username:
            raise ValueError("Blocked: Username is required for auditing!")
            
        # Mutate event metadata dynamically
        event._additional_metadata_tags.append("audited")

    # 2. Register Post-hook: Executed AFTER saving. Non-blocking.
    @atm.hook("post")
    def reporting_post_hook(event):
        nonlocal post_hook_fired
        post_hook_fired = True
        print(f"   [Post-Hook Triggered] Logged {event.token_count} tokens successfully.")

    # 3. Execute Valid Call
    with atm.context(username="audit-officer"):
        ev = atm.add_user_request("Auditable prompt content", token_count=15)
        
        assert pre_hook_fired is True
        assert post_hook_fired is True
        assert "audited" in ev._additional_metadata_tags

    # 4. Execute Invalid Call (Should raise ValueError)
    pre_hook_fired = False
    post_hook_fired = False
    
    try:
        # Lacks username -> Pre-hook raises ValueError
        atm.add_user_request("Anonymous prompt content", token_count=10)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"   Captured expected pre-hook validation error: {e}")
        assert pre_hook_fired is True
        assert post_hook_fired is False  # Storage and Post-hooks aborted!

    print("Hooks Validation Example complete! All assertions passed successfully.")

if __name__ == "__main__":
    run_example()

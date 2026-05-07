"""Example: Token Quota Limits & Quota Enforcement

This example showcases how to configure Scope-based Quotas (minute/hourly/daily caps) 
that strictly block further LLM calls by raising a TokenQuotaExceeded exception when breached.
"""

import agent_atm as atm

def run_example():
    print("Running Quota Enforcement Example...")
    
    atm.init(data_manager="in_memory")

    # 1. Configure Limit: Restrict app 'chat-widget' to 250 total tokens
    atm.limits.add(
        scope=atm.Scope(app="chat-widget"),
        quota=atm.Quota(total_limit=250),
        alert_level=atm.AlertLevel.BLOCKING
    )
    
    # 2. Execute within App Scope
    with atm.context(app_id="chat-widget"):
        
        # First request (150 tokens) -> below total_limit 250
        atm.add_user_request("Draft marketing copy.", token_count=150)
        
        # Second request (150 tokens) -> 150 + 150 = 300 > 250. Breach expected!
        try:
            atm.add_user_request("Draft option matrix.", token_count=150)
            assert False, "Should have breached token quota limit!"
        except atm.TokenQuotaExceeded as e:
            print(f"   Captured expected quota breach exception: {e}")
            
    # 3. Assert requests in other apps are unaffected
    with atm.context(app_id="internal-audit"):
        # This app has no limits registered, should complete cleanly
        ev = atm.add_user_request("Draft internal audit.", token_count=500)
        assert ev.token_count == 500

    print("Quota Enforcement Example complete! All assertions passed successfully.")

if __name__ == "__main__":
    run_example()

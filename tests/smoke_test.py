import agent_atm as atm

def test_smoke():
    print("Starting smoke test...")
    manager = atm.init(data_manager="in_memory")
    assert manager is not None
    print("Successfully initialized Agent Token Manager singleton.")
    
    # Record basic request
    event = atm.add_user_request("Smoke test prompt", token_count=5)
    assert event.token_count == 5
    print("Successfully recorded smoke test prompt event.")
    
    atm.shutdown()
    print("Smoke test completed successfully!")

if __name__ == "__main__":
    test_smoke()

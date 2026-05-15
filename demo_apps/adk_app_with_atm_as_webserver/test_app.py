import agent_atm as atm

def test_adk_webserver_telemetry():
    # Use in_memory for hermetic test validation of the remote client logic
    mgr = atm.init(data_manager="in_memory", default_app_id="adk-remote-bot")
    
    with atm.context(username="test_remote", session_id="sess_remote_1"):
        req = atm.add_user_request("Hello Remote", token_count=12)
        assert req.token_count == 12
        assert req.app_id == "adk-remote-bot"
        
        resp = atm.add_model_response("Hi Remote", token_count=34)
        assert resp.token_count == 34
        assert resp.app_id == "adk-remote-bot"

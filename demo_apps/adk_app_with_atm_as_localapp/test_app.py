import os
from token_manager import init_atm
import agent_atm as atm
import pytest

def test_adk_localapp_execution():
    if os.path.exists("app_usage.db"):
        os.remove("app_usage.db")
        
    init_atm()
    
    with atm.context(username="test_user", session_id="sess_test_1"):
        req = atm.add_user_request("Hello ADK", token_count=10)
        assert req.token_count == 10
        assert req.app_id == "adk-local-bot"
        
        resp = atm.add_model_response("Hi there", token_count=20)
        assert resp.token_count == 20
        assert resp.app_id == "adk-local-bot"
        
    if os.path.exists("app_usage.db"):
        os.remove("app_usage.db")

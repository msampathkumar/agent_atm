from datetime import datetime
import time
import pytest
import agent_atm as atm
from agent_atm.context import TokenEvent
from agent_atm.core import AgentTokenManager
from agent_atm.limits import TokenQuotaExceeded

# Simple mock class for a Google GenAI style response
class MockGoogleGenAIResponse:
    class UsageMetadata:
        def __init__(self):
            self.prompt_token_count = 15
            self.candidates_token_count = 25
            self.total_token_count = 40
            
    def __init__(self):
        self.usage_metadata = self.UsageMetadata()
        self.text = "Mocked response content"

def test_core_manual_token_override():
    atm_mgr = AgentTokenManager(data_manager="in_memory")
    
    ev = atm_mgr.add_user_request("Hello world!", token_count=5)
    assert ev.token_count == 5
    assert ev.event_type == "request"
    
    # Verify saved in memory
    assert atm_mgr.data_manager.get_usage() == 5

def test_core_default_tokenizer_calculation():
    atm_mgr = AgentTokenManager(data_manager="in_memory")
    
    ev = atm_mgr.add_user_request("Some text that will be tokenized by tiktoken or fallback")
    # Should count successfully (>0 tokens)
    assert ev.token_count > 0
    assert atm_mgr.data_manager.get_usage() == ev.token_count

def test_core_google_genai_extraction():
    atm_mgr = AgentTokenManager(data_manager="in_memory")
    mock_resp = MockGoogleGenAIResponse()
    
    # Test as model response
    ev_resp = atm_mgr.add_model_response(mock_resp)
    assert ev_resp.token_count == 25  # candidates_token_count
    
    # Test as request
    ev_req = atm_mgr.add_user_request(mock_resp)
    assert ev_req.token_count == 15  # prompt_token_count

def test_singleton_interface():
    # Initialize standard logging style singleton API
    atm.init(data_manager="in_memory", default_app_id="singleton-app")
    
    # Add user request
    ev = atm.add_user_request("Ping", token_count=1)
    assert ev.app_id == "singleton-app"
    assert ev.token_count == 1
    
    # Verify context scoping
    with atm.context(session_id="sess-xyz", username="clara"):
        ev2 = atm.add_model_response("Pong", token_count=2)
        assert ev2.session_id == "sess-xyz"
        assert ev2.username == "clara"
        assert ev2.app_id == "singleton-app"

def test_async_write():
    # Test background queue thread writer
    atm_mgr = AgentTokenManager(data_manager="in_memory", async_write=True)
    
    ev = atm_mgr.add_user_request("Async job text", token_count=10)
    assert ev.token_count == 10
    
    # Immediately checking data manager might be 0 (async write hasn't completed yet)
    # Give background worker a split second to process
    time.sleep(0.15)
    
    assert atm_mgr.data_manager.get_usage() == 10
    atm_mgr.shutdown()

def test_gemma3_tokenizer_support():
    # Verify our native dynamic import support for gemma.text.Gemma3Tokenizer!
    from gemma.text import Gemma3Tokenizer
    assert Gemma3Tokenizer is not None
    
    from unittest.mock import MagicMock
    mock_tokenizer = MagicMock(spec=Gemma3Tokenizer)
    # Mock the encode method to return a list of 6 token ids
    mock_tokenizer.encode.return_value = [10, 20, 30, 40, 50, 60]
    
    # Initialize global manager with custom Gemma3Tokenizer
    atm.init(data_manager="in_memory", tokenizer=mock_tokenizer)
    
    ev = atm.add_user_request("Hello Gemma 3 Model!")
    assert ev.token_count == 6
    
    # Verify that our mock tokenizer was indeed called to encode the string
    mock_tokenizer.encode.assert_called_once_with("Hello Gemma 3 Model!")

def test_gemma_tokenizer_integration_token_arrays():
    atm_mgr = AgentTokenManager(data_manager="in_memory")
    
    # 1. Pass a raw list of token IDs (integers)
    token_ids_list = [102, 4052, 19284, 33, 2, 1]
    ev_list = atm_mgr.add_model_response(token_ids_list)
    assert ev_list.token_count == 6
    
    # 2. Pass a custom object resembling JAX or numpy arrays of tokens
    class MockArray:
        def __init__(self, data):
            self.data = data
            self.ndim = 1
            self.shape = (len(data),)
            
        def tolist(self):
            return self.data
            
    mock_array = MockArray([1, 2, 3, 4])
    ev_array = atm_mgr.add_model_response(mock_array)
    assert ev_array.token_count == 4

def test_llm_payload_dataclass_support():
    from agent_atm.tokenizers.base import LLMPayload
    
    atm_mgr = AgentTokenManager(data_manager="in_memory")
    
    payload = LLMPayload(
        content="How does photosynthesis work?",
        model_id="gemini-ultra",
        _additional_metadata_tags=["science", "education"],
        _additional_metadata_config={"priority": "high"}
    )
    
    # Record the request passing the payload directly
    ev = atm_mgr.add_user_request(payload)
    
    assert ev.model_id == "gemini-ultra"
    assert ev.token_count > 0
    assert ev._additional_metadata_tags == ["science", "education"]
    assert ev._additional_metadata_config == {"priority": "high"}
def test_fastapi_post_telemetry():
    from fastapi.testclient import TestClient
    from agent_atm.dashboard.server import app
    
    client = TestClient(app)
    
    # Post a valid request event
    response = client.post("/api/events", json={
        "event_type": "request",
        "token_count": 200,
        "model_id": "gemini-2.5-flash",
        "username": "enterprise-user",
        "app_id": "distributed-app",
        "tags": ["network", "telemetry"],
        "config": {"node_id": "east-1"}
    })
    
    assert response.status_code == 201
    assert response.json()["status"] == "success"

from datetime import datetime
import pytest
import agent_atm as atm
from agent_atm import LLMPayload, TokenEvent
from agent_atm.types import LLMPayload as ModuleLLMPayload, TokenEvent as ModuleTokenEvent

def test_type_exposure_at_root():
    """Verify that LLMPayload and TokenEvent are correctly exposed at the root of the package."""
    assert LLMPayload is not None
    assert TokenEvent is not None
    assert atm.types.LLMPayload is LLMPayload
    assert atm.types.TokenEvent is TokenEvent

def test_llm_payload_validation_valid():
    """Verify that LLMPayload can be created with valid event types."""
    payload_req = LLMPayload(content="Hello request", event_type="request")
    assert payload_req.event_type == "request"

    payload_resp = LLMPayload(content="Hello response", event_type="response")
    assert payload_resp.event_type == "response"

def test_llm_payload_validation_invalid():
    """Verify that LLMPayload raises ValueError when event_type is invalid."""
    with pytest.raises(ValueError) as excinfo:
        LLMPayload(content="Bad request", event_type="invalid-type")
    assert "Invalid event_type: 'invalid-type'" in str(excinfo.value)

def test_token_event_validation_valid():
    """Verify that TokenEvent can be created with valid event types."""
    event_req = TokenEvent(
        timestamp=datetime.now(),
        event_type="request",
        token_count=10,
        model_id="test-model"
    )
    assert event_req.event_type == "request"

    event_resp = TokenEvent(
        timestamp=datetime.now(),
        event_type="response",
        token_count=20,
        model_id="test-model"
    )
    assert event_resp.event_type == "response"

def test_token_event_validation_invalid():
    """Verify that TokenEvent raises ValueError when event_type is invalid."""
    with pytest.raises(ValueError) as excinfo:
        TokenEvent(
            timestamp=datetime.now(),
            event_type="invalid-type",
            token_count=10,
            model_id="test-model"
        )
    assert "Invalid event_type: 'invalid-type'" in str(excinfo.value)

import socket
import threading
import time
import urllib.request
import json
import pytest
import os
from agent_atm import server, client, LLMPayload


def get_free_port() -> int:
    """Get a random free port from the OS."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def atm_server():
    port = get_free_port()
    db_path = "test_atm_server.db"

    # Remove DB if exists
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass

    # Start uvicorn server in a background daemon thread
    t = threading.Thread(
        target=server.run,
        kwargs={"host": "127.0.0.1", "port": port, "db_path": db_path, "reload": False},
        daemon=True,
    )
    t.start()

    # Wait/poll until server is healthy
    url = f"http://127.0.0.1:{port}/health"
    retries = 20
    success = False
    for _ in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=0.5) as resp:
                if resp.status == 200:
                    success = True
                    break
        except Exception:
            time.sleep(0.1)

    if not success:
        raise RuntimeError("Telemetry server failed to start in test time window.")

    yield f"http://127.0.0.1:{port}"

    # Cleanup DB file
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass


def test_sync_client(atm_server):
    c = client.Client(base_url=atm_server)

    res = c.send_event(
        event_type="request",
        token_count=150,
        model_id="gemini-pro",
        username="test-user-sync",
        session_id="session-sync-1",
        app_id="test-app",
        tags=["test", "sync"],
        config={"key": "value"},
    )

    assert res["status"] == "success"
    assert "Event successfully logged" in res["message"]


@pytest.mark.asyncio
async def test_async_client(atm_server):
    c = client.Client(base_url=atm_server)

    res = await c.send_event_async(
        event_type="response",
        token_count=250,
        model_id="gemini-pro-vision",
        username="test-user-async",
        session_id="session-async-1",
        app_id="test-app",
        tags=["test", "async"],
        config={"mode": "streaming"},
    )

    assert res["status"] == "success"
    assert "Event successfully logged" in res["message"]


def test_client_check_payload():
    c = client.Client()

    # Create simple payload
    payload = LLMPayload(
        content="Hello world, this is a simple test of token counting.",
        model_id="gpt-4",
        event_type="request",
        _additional_metadata_tags=["test-tag"],
        _additional_metadata_config={"env": "test"},
    )

    info = c.check_payload(payload)

    assert info["event_type"] == "request"
    assert info["model_id"] == "gpt-4"
    assert info["token_count"] > 0
    assert "Hello world" in info["text_preview"]
    assert "test-tag" in info["tags"]
    assert info["config"]["env"] == "test"


def test_client_send_payload(atm_server):
    c = client.Client(base_url=atm_server)

    payload = LLMPayload(
        content="Synchronous payload logging message.",
        model_id="gemma-7b",
        event_type="request",
        _additional_metadata_tags=["payload", "sync"],
        _additional_metadata_config={"method": "direct"},
    )

    res = c.send_payload(
        payload=payload,
        username="payload-sync-user",
        session_id="session-p-sync",
        app_id="payload-app",
    )

    assert res["status"] == "success"


@pytest.mark.asyncio
async def test_client_send_payload_async(atm_server):
    c = client.Client(base_url=atm_server)

    payload = LLMPayload(
        content="Asynchronous payload logging message.",
        model_id="gemma-2b",
        event_type="response",
        _additional_metadata_tags=["payload", "async"],
        _additional_metadata_config={"method": "direct-async"},
    )

    res = await c.send_payload_async(
        payload=payload,
        username="payload-async-user",
        session_id="session-p-async",
        app_id="payload-app",
    )

    assert res["status"] == "success"


def test_metrics_dynamic_window(atm_server):
    c = client.Client(base_url=atm_server)

    # Ensure some events are logged
    c.send_event(event_type="request", token_count=10, model_id="m1")
    c.send_event(event_type="response", token_count=20, model_id="m1")

    # Fetch metrics with 5m window
    url = f"{atm_server}/api/metrics?window=5m"
    with urllib.request.urlopen(url) as resp:
        metrics = json.loads(resp.read().decode("utf-8"))

    assert "stats" in metrics
    assert "chart_data" in metrics
    assert metrics["stats"]["total_tokens"] >= 30
    assert metrics["stats"]["total_request_tokens"] >= 10
    assert metrics["stats"]["total_response_tokens"] >= 20
    assert len(metrics["chart_data"]) == 12
    assert "request_tokens" in metrics["chart_data"][0]
    assert "response_tokens" in metrics["chart_data"][0]
    assert "total_tokens" in metrics["chart_data"][0]


def test_client_error_handling(atm_server):
    c = client.Client(base_url=atm_server)

    # Try logging an invalid event type to trigger server-side 400 validation
    with pytest.raises(RuntimeError) as exc_info:
        c.send_event(event_type="invalid-type", token_count=100, model_id="m1")
    assert "ATM Server error" in str(exc_info.value)


def test_metrics_all_windows(atm_server):
    c = client.Client(base_url=atm_server)
    assert c, "Failed to create client"

    windows = [
        "1m",
        "7d",
        "3d",
        "1d",
        "12h",
        "6h",
        "4h",
        "2h",
        "1h",
        "30m",
        "15m",
        "5m",
    ]
    for win in windows:
        url = f"{atm_server}/api/metrics?window={win}"
        with urllib.request.urlopen(url) as resp:
            metrics = json.loads(resp.read().decode("utf-8"))

        assert "stats" in metrics
        assert "chart_data" in metrics
        assert len(metrics["chart_data"]) == 12


def test_client_check_payload_override():
    c = client.Client()

    payload = LLMPayload(
        content="Some message text here.",
        model_id="gpt-4",
        token_count_override=42,
        event_type="response",
    )

    info = c.check_payload(payload)
    assert info["token_count"] == 42
    assert info["event_type"] == "response"

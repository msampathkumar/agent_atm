import asyncio
import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from agent_atm.types import LLMPayload
from agent_atm.tokenizers.base import DefaultTokenizer
from agent_atm.tokenizers.google_genai import GoogleGenAITokenizer
from agent_atm.tokenizers.gemma import GemmaTokenizerIntegration


class Client:
    """Client to interact with the Agent Token Manager (ATM) telemetry server.

    Supports both synchronous and asynchronous requests using only standard library tools.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")
        self.tokenizer_integrations = [
            GemmaTokenizerIntegration(),
            GoogleGenAITokenizer(),
            DefaultTokenizer(),
        ]

    def _resolve_token_count_and_text(self, payload: LLMPayload) -> tuple[int, str]:
        """Calculate token count and get the raw text from an LLMPayload."""
        if payload.token_count_override is not None:
            # Extract text preview if possible
            text = ""
            for integration in self.tokenizer_integrations:
                try:
                    if integration.can_handle(payload):
                        text, _ = integration.extract_text_and_tokens(payload)
                        break
                except Exception:
                    pass
            if not text:
                text = str(payload.content)
            return payload.token_count_override, text

        for integration in self.tokenizer_integrations:
            try:
                if integration.can_handle(payload):
                    text, count = integration.extract_text_and_tokens(payload)
                    return count, text
            except Exception:
                pass

        text = str(payload.content)
        # Fallback simple heuristic count
        char_estimate = max(1, len(text) // 4)
        return char_estimate, text

    def check_payload(self, payload: LLMPayload) -> Dict[str, Any]:
        """Check the token count and preview content of an LLMPayload without sending it to the server."""
        tokens, text = self._resolve_token_count_and_text(payload)
        return {
            "event_type": payload.event_type,
            "token_count": tokens,
            "model_id": payload.model_id,
            "text_preview": text[:200] + "..." if len(text) > 200 else text,
            "tags": payload._additional_metadata_tags,
            "config": payload._additional_metadata_config,
        }

    def send_payload(
        self,
        payload: LLMPayload,
        username: Optional[str] = None,
        session_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an LLMPayload token telemetry event to the ATM server synchronously."""
        tokens, _ = self._resolve_token_count_and_text(payload)

        return self.send_event(
            event_type=payload.event_type,
            token_count=tokens,
            model_id=payload.model_id,
            username=username,
            session_id=session_id,
            app_id=app_id,
            tags=payload._additional_metadata_tags,
            config=payload._additional_metadata_config,
        )

    async def send_payload_async(
        self,
        payload: LLMPayload,
        username: Optional[str] = None,
        session_id: Optional[str] = None,
        app_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an LLMPayload token telemetry event to the ATM server asynchronously."""
        return await asyncio.to_thread(
            self.send_payload,
            payload=payload,
            username=username,
            session_id=session_id,
            app_id=app_id,
        )

    def send_event(
        self,
        event_type: str,
        token_count: int,
        model_id: str,
        username: Optional[str] = None,
        session_id: Optional[str] = None,
        app_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a token telemetry event to the ATM server synchronously.

        Args:
            event_type: Must be either 'request' or 'response'.
            token_count: The number of tokens consumed.
            model_id: The identifier of the LLM model used.
            username: Optional username associated with the request.
            session_id: Optional session identifier.
            app_id: Optional application identifier.
            tags: Optional list of descriptive tags.
            config: Optional key-value configuration dictionary.

        Returns:
            A dictionary containing the server's response JSON.

        Raises:
            RuntimeError: If the request fails or the server returns an error.
        """
        url = f"{self.base_url}/api/events"
        payload = {
            "event_type": event_type,
            "token_count": token_count,
            "model_id": model_id,
            "username": username,
            "session_id": session_id,
            "app_id": app_id,
            "tags": tags or [],
            "config": config or {},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode("utf-8")
                detail = json.loads(error_body).get("detail", error_body)
            except Exception:
                detail = str(e)
            raise RuntimeError(f"ATM Server error ({e.code}): {detail}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to connect to ATM Server at {url}: {e}") from e

    async def send_event_async(
        self,
        event_type: str,
        token_count: int,
        model_id: str,
        username: Optional[str] = None,
        session_id: Optional[str] = None,
        app_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a token telemetry event to the ATM server asynchronously.

        Uses asyncio.to_thread to avoid blocking the event loop during HTTP requests.
        """
        return await asyncio.to_thread(
            self.send_event,
            event_type=event_type,
            token_count=token_count,
            model_id=model_id,
            username=username,
            session_id=session_id,
            app_id=app_id,
            tags=tags,
            config=config,
        )


from datetime import datetime
from agent_atm.data_managers.base import BaseDataManager
from agent_atm.types import TokenEvent


class RemoteHTTPDataManager(BaseDataManager):
    """Data Manager that sends telemetry events to a remote ATM server via HTTP."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.client = Client(base_url=base_url)

    def save(self, event: TokenEvent) -> None:
        self.client.send_event(
            event_type=event.event_type,
            token_count=event.token_count,
            model_id=event.model_id,
            username=event.username,
            session_id=event.session_id,
            app_id=event.app_id,
            tags=event._additional_metadata_tags,
            config=event._additional_metadata_config,
        )

    def get_usage(
        self,
        app_id: Optional[str] = None,
        username: Optional[str] = None,
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        # Remote usage queries are not supported by default
        return 0


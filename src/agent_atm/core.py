import atexit
from datetime import datetime
import queue
import threading
from typing import Any, Dict, List, Literal, Optional, Union

from agent_atm.context import get_current_context
from agent_atm.data_managers.base import BaseDataManager
from agent_atm.data_managers.in_memory import InMemoryManager
from agent_atm.data_managers.sqlite import SqliteManager
from agent_atm.types import TokenEvent, LLMPayload
from agent_atm.hooks.registry import HookRegistry
from agent_atm.limits.registry import LimitRegistry
from agent_atm.tokenizers.base import BaseTokenizerIntegration, DefaultTokenizer
from agent_atm.tokenizers.google_genai import GoogleGenAITokenizer
from agent_atm.tokenizers.gemma import GemmaTokenizerIntegration




import logging

logger = logging.getLogger("agent_atm")


class CachedDataManagerProxy:
    """Proxy wrapper around BaseDataManager that caches get_usage_summary to prevent DB bottleneck."""
    def __init__(self, data_manager: BaseDataManager, cache_driver: str = "disk"):
        from agent_atm.cache import get_store
        self.data_manager = data_manager
        self.cache = get_store(cache_driver)

    def save(self, event) -> None:
        logger.debug("Saving event via CachedDataManagerProxy")
        self.data_manager.save(event)
        self.cache.clear()

    def get_usage(self, *args, **kwargs) -> int:
        return self.data_manager.get_usage(*args, **kwargs)

    def get_usage_summary(self, app_id=None, username=None, session_id=None):
        if not hasattr(self.data_manager, "get_usage_summary"):
            return {"total": 0, "day": 0, "hour": 0, "minute": 0}
        key = f"usage_{app_id}_{username}_{session_id}"
        cached = self.cache.get(key)
        if cached:
            return cached
        fresh = self.data_manager.get_usage_summary(app_id, username, session_id)
        self.cache.set(key, fresh, ttl=10)
        return fresh

    def __getattr__(self, item):
        return getattr(self.data_manager, item)


class AgentTokenManager:
    """Core manager coordinating token parsing, hook validations, and data storage."""
    
    def __init__(
        self,
        data_manager: Union[str, BaseDataManager] = "in_memory",
        async_write: bool = False,
        db_path: str = "agent_atm.db",
        default_app_id: Optional[str] = None,
        tokenizer: Optional[Any] = None,
        telemetry_failure_policy: str = "fail",
        quota_cache: Optional[str] = None,
        **kwargs
    ):
        logger.info(f"Initializing AgentTokenManager with data_manager='{data_manager}', quota_cache='{quota_cache}'")
        self.default_app_id = default_app_id
        self.telemetry_failure_policy = telemetry_failure_policy
        self.buffer_file_path = ".agent_atm_failed_events.jsonl"

        # Initialize dynamic Rule Engine
        from agent_atm.rules.engine import RuleEngine
        self.rule_engine = RuleEngine()

        # Initialize Data Manager
        from agent_atm.data_managers import get_data_manager
        self.data_manager = get_data_manager(data_manager, db_url=db_path, **kwargs)

        if quota_cache:
            self.data_manager = CachedDataManagerProxy(self.data_manager, cache_driver=quota_cache)

        # Initialize hook, quota registries, and tokenizer integrations
        self.hooks = HookRegistry()
        self.limits = LimitRegistry()
        self.tokenizer_integrations: List[BaseTokenizerIntegration] = [
            GemmaTokenizerIntegration(),
            GoogleGenAITokenizer(),
            DefaultTokenizer(custom_tokenizer=tokenizer)  # Fallback tokenizer is always last
        ]



        # Setup Async Background Worker if requested
        self.async_write = async_write
        self._queue: Optional[queue.Queue] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        if self.async_write:
            self._start_async_worker()
            atexit.register(self.shutdown)

    def _start_async_worker(self) -> None:
        self._queue = queue.Queue()
        self._worker_thread = threading.Thread(
            target=self._worker_loop, 
            name="agent-atm-async-writer", 
            daemon=True
        )
        self._worker_thread.start()

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                # Wait short time to avoid tight CPU loops
                event = self._queue.get(timeout=0.1)
                self._save_sync(event)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                import sys
                print(f"[agent-atm] Error in background writer thread: {e}", file=sys.stderr)

    def _save_sync(self, event: TokenEvent) -> None:
        self.data_manager.save(event)

    def shutdown(self) -> None:
        """Gracefully drain and terminate the background writer thread."""
        if self.async_write and self._worker_thread:
            self._stop_event.set()
            self._worker_thread.join(timeout=3.0)
            self._worker_thread = None

    def _process_event(
        self, 
        event_type: Literal["request", "response"], 
        content: Any = None, 
        token_count: Optional[int] = None,
        model_id: str = "default",
        username: Optional[str] = None,
        session_id: Optional[str] = None,
        app_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> TokenEvent:
        # Retrieve thread/async local metadata context and resolve hierarchies
        context = get_current_context()
        
        final_app_id = app_id or context.get("app_id") or self.default_app_id
        final_username = username or context.get("username")
        final_session_id = session_id or context.get("session_id")
        
        # Merge tags safely
        final_tags = list(context.get("_additional_metadata_tags", []))
        if tags:
            final_tags.extend(tags)
            
        # Merge custom metadata key-values
        final_config = dict(context.get("_additional_metadata_config", {}))

        # 1. Build or extract structured LLMPayload dataclass
        if isinstance(content, LLMPayload):
            payload = content
            if token_count is not None:
                payload.token_count_override = token_count
            if model_id != "default":
                payload.model_id = model_id
            # Merge local arguments with payload metadata
            for t in final_tags:
                if t not in payload._additional_metadata_tags:
                    payload._additional_metadata_tags.append(t)
            payload._additional_metadata_config.update(final_config)
        else:
            payload = LLMPayload(
                content=content,
                model_id=model_id,
                token_count_override=token_count,
                event_type=event_type,
                _additional_metadata_tags=final_tags,
                _additional_metadata_config=final_config
            )

        # 2. Extract token count and text if token count is not explicitly override
        final_token_count = payload.token_count_override
        if final_token_count is None:
            extracted_text = ""
            extracted_tokens = 0
            for integration in self.tokenizer_integrations:
                if integration.can_handle(payload):
                    extracted_text, extracted_tokens = integration.extract_text_and_tokens(payload)
                    break
            final_token_count = extracted_tokens

        # 3. Assemble TokenEvent
        event = TokenEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            token_count=final_token_count,
            model_id=payload.model_id,
            username=final_username,
            session_id=final_session_id,
            app_id=final_app_id,
            _additional_metadata_tags=payload._additional_metadata_tags,
            _additional_metadata_config=payload._additional_metadata_config
        )
        logger.debug(f"Processing {event_type} event: {event.token_count} tokens for model '{event.model_id}'")

        # 4. Trigger Pre-hooks validation
        self.hooks.trigger_pre_hooks(event)

        # 5. Validate against registered token quota limits (Only on User request events!)
        if event_type == "request":
            # A: Local limits rules
            self.limits.validate(event, self.data_manager)
            # B: App-level custom rules
            self.rule_engine.validate_app_rules(event)
            # C: DB-level custom rules
            self.rule_engine.validate_db_rules(event, self.data_manager)

        # 6. Save the Event & Handle Severity Policies
        # Try to replay buffered records first (if any)
        self._replay_buffered_events()

        try:
            if self.async_write and self._queue:
                self._queue.put(event)
            else:
                self._save_sync(event)
        except Exception as e:
            self._handle_telemetry_failure(event, e)

        # 7. Trigger Post-hooks notification
        self.hooks.trigger_post_hooks(event)

        return event

    def add_user_request(
        self, 
        content: Any = None, 
        token_count: Optional[int] = None,
        model_id: str = "default",
        username: Optional[str] = None,
        session_id: Optional[str] = None,
        app_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> TokenEvent:
        """Record a user request event."""
        return self._process_event(
            "request", content, token_count, model_id, username, session_id, app_id, tags
        )

    def add_model_response(
        self, 
        content: Any = None, 
        token_count: Optional[int] = None,
        model_id: str = "default",
        username: Optional[str] = None,
        session_id: Optional[str] = None,
        app_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> TokenEvent:
        """Record a model response event."""
        return self._process_event(
            "response", content, token_count, model_id, username, session_id, app_id, tags
        )

    def _handle_telemetry_failure(self, event: TokenEvent, exc: Exception) -> None:
        import json
        import sys

        if self.telemetry_failure_policy == "fail":
            raise exc

        # Serialize the event payload to save locally
        event_dict = {
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "token_count": event.token_count,
            "model_id": event.model_id,
            "username": event.username,
            "session_id": event.session_id,
            "app_id": event.app_id,
            "hostname": event.hostname,
            "tags": event._additional_metadata_tags,
            "config": event._additional_metadata_config
        }

        # Append to the local buffer file
        try:
            with open(self.buffer_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event_dict) + "\n")
        except Exception as file_err:
            logger.error(f"Error writing telemetry to local buffer file: {file_err}")

        if self.telemetry_failure_policy == "warn":
            logger.warning(f"Telemetry submission failed. Warning logged & event archived locally. Error: {exc}")

    def _replay_buffered_events(self) -> None:
        import json
        import os
        from datetime import datetime

        if not os.path.exists(self.buffer_file_path):
            return

        # If policy is "warn", we do not perform auto-replay
        if self.telemetry_failure_policy == "warn":
            return

        buffered_lines = []
        try:
            with open(self.buffer_file_path, "r", encoding="utf-8") as f:
                buffered_lines = f.readlines()
        except Exception:
            return

        if not buffered_lines:
            return

        remaining_lines = []
        success_count = 0

        for line in buffered_lines:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                ev = TokenEvent(
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    event_type=data["event_type"],
                    token_count=data["token_count"],
                    model_id=data["model_id"],
                    username=data["username"],
                    session_id=data["session_id"],
                    app_id=data["app_id"],
                    hostname=data["hostname"],
                    _additional_metadata_tags=data.get("tags", []),
                    _additional_metadata_config=data.get("config", {})
                )
                self._save_sync(ev)
                success_count += 1
            except Exception:
                remaining_lines.append(line)

        try:
            if remaining_lines:
                with open(self.buffer_file_path, "w", encoding="utf-8") as f:
                    for r_line in remaining_lines:
                        f.write(r_line + "\n")
            else:
                os.remove(self.buffer_file_path)
        except Exception:
            pass


import atexit
from datetime import datetime
import queue
import threading
from typing import Any, Dict, List, Optional, Union

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




class AgentTokenManager:
    """Core manager coordinating token parsing, hook validations, and data storage."""
    
    def __init__(
        self,
        data_manager: Union[str, BaseDataManager] = "in_memory",
        async_write: bool = False,
        db_path: str = "agent_atm.db",
        default_app_id: Optional[str] = None,
        tokenizer: Optional[Any] = None
    ):
        self.default_app_id = default_app_id
        
        # Initialize Data Manager
        if isinstance(data_manager, str):
            if data_manager == "in_memory":
                self.data_manager: BaseDataManager = InMemoryManager()
            elif data_manager == "sqlite":
                self.data_manager = SqliteManager(db_path=db_path)
            else:
                raise ValueError(f"Unknown storage manager shorthand: {data_manager}")
        else:
            self.data_manager = data_manager

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
        event_type: str, 
        content: Any, 
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

        # 4. Trigger Pre-hooks validation
        self.hooks.trigger_pre_hooks(event)

        # 5. Validate against registered token quota limits
        self.limits.validate(event, self.data_manager)

        # 6. Save the Event
        if self.async_write and self._queue:
            self._queue.put(event)
        else:
            self._save_sync(event)

        # 7. Trigger Post-hooks notification
        self.hooks.trigger_post_hooks(event)

        return event

    def add_user_request(
        self, 
        content: Any, 
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
        content: Any, 
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

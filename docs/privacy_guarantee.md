# Privacy-First Guarantee Technical Verification

This document outlines the structural, code-level verification of the **Privacy-First Guarantee** provided by the `agent-atm` SDK. 

`agent-atm` acts strictly as a numerical statistics and metadata tracker. **Zero raw prompt or response content text is ever persisted or cached outside of local transient memory.**

---

## 🛠️ Code-Level Verification

Below is the structural analysis of how telemetry data flows through the SDK, demonstrating that conversational text content is immediately discarded after tokenization.

### 1. Transient in-Memory Extraction
When you log an event via `add_user_request` or `add_model_response`, the raw content is wrapped strictly inside a temporary memory object:

* **[LLMPayload](file:///Users/sampathm/github/agent_token_manager/agent_atm/types/payload.py)**:
  ```python
  @dataclass
  class LLMPayload:
      content: Any  # Raw string, Google GenAI Response, Gemma token arrays, etc.
      model_id: str = "default"
      token_count_override: Optional[int] = None
      ...
  ```
The payload holds the text content temporarily while passing it into active tokenizer integrations to compute the exact integer token count.

### 2. Discarding Content in the Processing Pipeline
In the core event coordinator ([agent_atm/core.py](file:///Users/sampathm/github/agent_token_manager/agent_atm/core.py#L146-L185)):
* The token count is computed from `payload.content`.
* Immediately after, **only** the resulting integer count, model ID, timestamp, and user-scoped metadata are copied to create the `TokenEvent`.
* The raw `payload` and `content` parameters are **never** added to the event and are completely left out:
  ```python
  # Assemble TokenEvent - Raw text content is completely excluded!
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
  ```
Once `_process_event` completes execution, the local references to the text strings are released, allowing Python's garbage collector to instantly clear them from RAM.

### 3. Clean Immutable Telemetry Record
The compiled [TokenEvent](file:///Users/sampathm/github/agent_token_manager/agent_atm/types/event.py) contains **no fields** allocated for raw prompt or response content:
```python
@dataclass
class TokenEvent:
    timestamp: datetime
    event_type: str  # "request" or "response"
    token_count: int
    model_id: str
    username: Optional[str] = None
    session_id: Optional[str] = None
    app_id: Optional[str] = None
    hostname: Optional[str] = field(default_factory=socket.gethostname)
    _additional_metadata_tags: List[str] = field(default_factory=list)
    _additional_metadata_config: Dict[str, str] = field(default_factory=dict)
```

### 4. No Database Persistence of Text Content
* **SQLite Manager**: In [sqlite.py](file:///Users/sampathm/github/agent_token_manager/agent_atm/data_managers/sqlite.py#L34-L47), the `token_events` database table has no text or binary blob columns designed for conversational data.
* **In-Memory Manager**: In [in_memory.py](file:///Users/sampathm/github/agent_token_manager/agent_atm/data_managers/in_memory.py), it stores a clean list of `TokenEvent` records in memory, retaining no link to the original text query.

---

## 🔒 Privacy Summary
`agent-atm` operates with a strict security boundary: **Conversational text never crosses the boundary from transient volatile RAM to storage.** You can confidently run this SDK in highly secure, private, or enterprise environments without any risk of customer prompt leakages.

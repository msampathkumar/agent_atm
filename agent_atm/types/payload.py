"""Module Purpose: Defines the structured LLMPayload tokenizer input data class.

Module Function: Provides a typed, explicit parameter interface passed into all Tokenizer Integrations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

@dataclass
class LLMPayload:
    """Structured parameter wrapper passed to all Tokenizer Integrations in agent-atm.

    This class encapsulates the raw content to be processed (such as a prompt string,
    a Google GenAI Client Response, or Gemma token array) along with optional metadata overrides
    and configurations.

    Lifecycle & Database Mapping:
    ----------------------------
    1. An `LLMPayload` is created either explicitly by the user or implicitly inside
       `atm.add_user_request()` / `atm.add_model_response()`.
    2. The Tokenizer Integrations parse the `content` within `LLMPayload` to count tokens.
    3. The resolved token count, event type, and metadata from `LLMPayload` are transferred
       to a new `TokenEvent` instance.
    4. The `TokenEvent` is then processed by pre-hooks and limits validation, and finally
       persisted to the database (SQLite, in-memory, etc.) via the configured `DataManager`.

    Validation:
    -----------
    - `event_type` is strictly validated to be either "request" or "response".
      An exception (ValueError) is raised at instantiation time if any other value is passed.
    """
    # Essentials
    content: Any  # Raw string, Google GenAI Response, Gemma token arrays, or client objects.
    
    # Optionals
    model_id: str = "default"
    token_count_override: Optional[int] = None
    event_type: Literal["request", "response"] = "request"  # Must be "request" or "response"
    
    # Standardized Metadata
    _additional_metadata_tags: List[str] = field(default_factory=list)
    _additional_metadata_config: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate fields upon initialization."""
        if self.event_type not in ("request", "response"):
            raise ValueError(
                f"Invalid event_type: '{self.event_type}'. "
                "LLMPayload event_type must be either 'request' or 'response'."
            )


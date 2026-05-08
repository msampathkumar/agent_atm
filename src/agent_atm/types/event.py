"""Module Purpose: Defines the core TokenEvent telemetry data structure.

Module Function: Acts as the immutable baseline record representing a captured token consumption event.
"""

from dataclasses import dataclass, field
from datetime import datetime
import socket
from typing import Dict, List, Literal, Optional

@dataclass
class TokenEvent:
    """Core immutable telemetry record representing a captured token consumption event.

    Attributes:
        timestamp: The precise UTC datetime when the token usage event was tracked.
        event_type: Either "request" (input/prompt tokens) or "response" (output/candidate tokens).
        token_count: The parsed or overridden number of tokens consumed.
        model_id: The identifier of the LLM used (e.g. "gemini-2.5-flash").
        username: Optional identifier representing the application user consuming tokens.
        session_id: Optional identifier grouping events under a cohesive workflow session.
        app_id: Optional identifier attributing the event to a specific microservice or bot instance.
        hostname: The machine host where the token consumption took place.
        _additional_metadata_tags: Non-unique tags used to slice and filter analytics.
        _additional_metadata_config: Arbitrary key-value telemetry scope metadata parameters.

    Validation:
    -----------
    - `event_type` is strictly validated to be either "request" or "response" on creation.
      Throws `ValueError` otherwise.
    """
    # Essentials
    timestamp: datetime
    event_type: Literal["request", "response"]  # Must be either "request" or "response"
    token_count: int
    model_id: str
    
    # Optionals
    username: Optional[str] = None
    session_id: Optional[str] = None
    app_id: Optional[str] = None
    hostname: Optional[str] = field(default_factory=socket.gethostname)
    
    # Standardized Metadata
    _additional_metadata_tags: List[str] = field(default_factory=list)
    _additional_metadata_config: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate fields upon initialization."""
        if self.event_type not in ("request", "response"):
            raise ValueError(
                f"Invalid event_type: '{self.event_type}'. "
                "TokenEvent event_type must be either 'request' or 'response'."
            )


"""Module Purpose: Defines the structured LLMPayload tokenizer input data class.

Module Function: Provides a typed, explicit parameter interface passed into all Tokenizer Integrations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class LLMPayload:
    """Structured wrapper passed to all Tokenizer Integrations, providing explicit type fields."""
    # Essentials
    content: Any  # Raw string, Google GenAI Response, Gemma token arrays, or client objects.
    
    # Optionals
    model_id: str = "default"
    token_count_override: Optional[int] = None
    event_type: str = "request"  # Either "request" or "response"
    
    # Standardized Metadata
    _additional_metadata_tags: List[str] = field(default_factory=list)
    _additional_metadata_config: Dict[str, str] = field(default_factory=dict)

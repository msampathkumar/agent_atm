"""Module Purpose: Defines the core TokenEvent telemetry data structure.

Module Function: Acts as the immutable baseline record representing a captured token consumption event.
"""

from dataclasses import dataclass, field
from datetime import datetime
import socket
from typing import Dict, List, Optional

@dataclass
class TokenEvent:
    # Essentials
    timestamp: datetime
    event_type: str  # "request" or "response"
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

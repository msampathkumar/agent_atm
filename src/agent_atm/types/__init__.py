"""Module Purpose: Unified Type Repository & Validation Contract Registry.

This module defines and exports the central data-transfer objects (DTOs), 
limiting definitions, and validation structures used throughout the `agent-atm` SDK.

Why This Module Exists:
----------------------
1. **Decoupling & Architecture**: Separating data models from runtime coordination 
   prevents import loops (circular dependencies) between tokenizers, data managers, 
   hook registries, and context management.
2. **Data Consistency**: Enforcing static and dynamic validation invariants 
   at data entry points ensures that all metric records adhere to strict validation
   rules before any storage commits.
3. **Unified Contract**: Provides developers a clean, singular import repository 
   to reference structured inputs (`LLMPayload`), persistent storage events 
   (`TokenEvent`), and system budget quotas (`Scope`, `Quota`, `LimitRule`).

How It Helps & Pipeline Flow:
-----------------------------
- **Client Input Phase (`LLMPayload`)**: Wraps raw multi-format content (prompt strings, 
  GenAI SDK responses, token arrays) with localized metadata and enforces strict `event_type` 
  constraints ("request" / "response") during object construction.
- **Parsing & Conversion**: Tokenizer integrations parse the payload, calculate counts, 
  and transition the transient `LLMPayload` parameters cleanly into a `TokenEvent`.
- **Enforcement & Persistence (`TokenEvent`)**: Represents the immutable, validated 
  telemetry event passed through pre-hooks, checked against quota caps, and loaded 
  into SQLite/In-Memory databases for analytics rendering.
"""

from agent_atm.types.event import TokenEvent
from agent_atm.types.payload import LLMPayload
from agent_atm.types.limit import AlertLevel, Scope, Quota, LimitRule

__all__ = [
    "TokenEvent",
    "LLMPayload",
    "AlertLevel",
    "Scope",
    "Quota",
    "LimitRule"
]

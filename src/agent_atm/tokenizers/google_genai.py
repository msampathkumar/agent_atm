"""Module Purpose: Implements automatic token counting and text parsing for Google GenAI clients.

Module Function: Duck-types Response and UsageMetadata properties to natively extract Gemini token statistics.
"""

from typing import Any, Tuple
from agent_atm.tokenizers.base import BaseTokenizerIntegration, LLMPayload

class GoogleGenAITokenizer(BaseTokenizerIntegration):
    """Auto-extracts text content and exact token counts from Google GenAI Response objects."""

    def can_handle(self, payload: LLMPayload) -> bool:
        # Duck-typing check for Google GenAI Response objects inside payload.content
        obj = payload.content
        return hasattr(obj, "usage_metadata") and (hasattr(obj, "text") or hasattr(obj, "candidates"))

    def extract_text_and_tokens(self, payload: LLMPayload) -> Tuple[str, int]:
        obj = payload.content
        
        # Extract text if available (usually on the response object)
        text = ""
        try:
            text = getattr(obj, "text", "")
            if callable(text):
                text = text()
        except Exception:
            pass

        # Extract usage metadata from the response object
        usage = getattr(obj, "usage_metadata", None)
        tokens = 0
        if usage:
            if payload.event_type == "request":
                tokens = getattr(usage, "prompt_token_count", 0)
            else:
                tokens = getattr(usage, "candidates_token_count", 0)
                # Fallback to total - prompt if candidate count is missing but total is present
                if not tokens:
                    total = getattr(usage, "total_token_count", 0)
                    prompt = getattr(usage, "prompt_token_count", 0)
                    tokens = max(0, total - prompt)

        # Fallback: if token count couldn't be parsed from usage metadata but text is present,
        # estimate using heuristic
        if not tokens and text:
            char_estimate = max(1, len(text) // 4)
            word_estimate = max(1, int(len(text.split()) * 1.3))
            tokens = (char_estimate + word_estimate) // 2

        return text, tokens

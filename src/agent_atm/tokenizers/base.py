"""Module Purpose: Defines the base abstract class for Tokenizer Integrations and fallbacks.

Module Function: Governs how different LLM content structures are parsed and calculated.
"""

from abc import ABC, abstractmethod
from typing import Any, Tuple, Optional

# ==============================================================================
# DEPRECATED: LLMPayload class has been moved to agent_atm/types/payload.py.
# Rationale: Modularized types folder holds all core data structure dataclasses.
# ==============================================================================
# @dataclass
# class LLMPayload:
#     content: Any
#     model_id: str = "default"
#     token_count_override: Optional[int] = None
#     event_type: str = "request"
#     _additional_metadata_tags: List[str] = field(default_factory=list)
#     _additional_metadata_config: Dict[str, str] = field(default_factory=dict)

from agent_atm.types import LLMPayload

class BaseTokenizerIntegration(ABC):
    """Base abstract class for LLM SDK client request/response integrations."""
    
    @abstractmethod
    def can_handle(self, payload: LLMPayload) -> bool:
        """Determine if this integration wrapper can handle the given LLMPayload content.
        
        Args:
            payload: The structured LLMPayload dataclass containing raw content and metadata.
            
        Returns:
            True if this integration can parse the payload, False otherwise.
        """
        pass

    @abstractmethod
    def extract_text_and_tokens(self, payload: LLMPayload) -> Tuple[str, int]:
        """Extract raw text content and calculated token count from the LLMPayload.
        
        Args:
            payload: The structured LLMPayload dataclass.
            
        Returns:
            A tuple of (extracted_text, token_count).
        """
        pass

class DefaultTokenizer(BaseTokenizerIntegration):
    """Default tokenizer mapping supporting direct strings, with tiktoken/gemma support & heuristic fallback."""
    
    def __init__(self, custom_tokenizer: Optional[Any] = None):
        self.custom_tokenizer = custom_tokenizer
        self._encoding = None
        
        if custom_tokenizer is None:
            try:
                import tiktoken
                # Use standard OpenAI cl100k_base (gpt-4/gpt-3.5-turbo) encoding as general SDK baseline approximation
                self._encoding = tiktoken.get_encoding("cl100k_base")
            except ImportError:
                pass

    def can_handle(self, payload: LLMPayload) -> bool:
        # Default handler can accept strings or anything converting to string
        obj = payload.content
        return isinstance(obj, str) or hasattr(obj, "__str__")

    def extract_text_and_tokens(self, payload: LLMPayload) -> Tuple[str, int]:
        text = str(payload.content)
        
        # 1. Use custom tokenizer if registered
        if self.custom_tokenizer:
            try:
                if hasattr(self.custom_tokenizer, "encode"):
                    tokens = len(self.custom_tokenizer.encode(text))
                    return text, tokens
            except Exception:
                pass
                
        # 2. Use default tiktoken encoding
        if self._encoding:
            try:
                tokens = len(self._encoding.encode(text))
                return text, tokens
            except Exception:
                pass
                
        # 3. Heuristic count fallback
        tokens = self._heuristic_count(text)
        return text, tokens

    def _heuristic_count(self, text: str) -> int:
        # Heuristic: 1 token is approximately 4 characters or 0.75 words
        if not text:
            return 0
        char_estimate = max(1, len(text) // 4)
        word_estimate = max(1, int(len(text.split()) * 1.3))
        return (char_estimate + word_estimate) // 2

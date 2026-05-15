"""Module Purpose: Implements automatic token extraction for Google DeepMind Gemma models.

Module Function: Integrates import shims for gemma.text and parses list/array sampler outputs.
"""

import sys
from typing import Any, Tuple
from agent_atm.tokenizers.base import BaseTokenizerIntegration, LLMPayload

# Dynamic sys.modules import alias for gemma.text -> gemma.gm.text
try:
    from unittest.mock import MagicMock
    if "kauldron.utils" not in sys.modules:
        sys.modules["kauldron.utils"] = MagicMock()
    if "kauldron" not in sys.modules:
        sys.modules["kauldron"] = MagicMock()
    from gemma import gm
    sys.modules["gemma.text"] = gm.text
except ImportError:
    pass

class GemmaTokenizerIntegration(BaseTokenizerIntegration):
    """Auto-extracts tokens and text from Gemma outputs, samplers, and token arrays."""

    def can_handle(self, payload: LLMPayload) -> bool:
        obj = payload.content
        
        # 1. Check if it is a Gemma Tokenizer instance itself
        cls_name = obj.__class__.__name__
        if "Gemma" in cls_name and "Tokenizer" in cls_name:
            return True
            
        # 2. Check if it is a list of integers (token IDs) or a JAX/numpy array of tokens
        if isinstance(obj, list) and len(obj) > 0 and all(isinstance(x, int) for x in obj):
            return True
            
        # Check if it's a numpy/JAX array of token IDs
        if hasattr(obj, "shape") and hasattr(obj, "tolist") and hasattr(obj, "ndim"):
            return True
            
        return False

    def extract_text_and_tokens(self, payload: LLMPayload) -> Tuple[str, int]:
        obj = payload.content
        
        # If the object is a tokenizer itself, we don't count it directly as a value
        cls_name = obj.__class__.__name__
        if "Gemma" in cls_name and "Tokenizer" in cls_name:
            return "", 0

        # If it is a list of token IDs
        if isinstance(obj, list):
            return "", len(obj)

        # If it is a numpy or JAX array of token IDs
        if hasattr(obj, "shape") and hasattr(obj, "tolist") and hasattr(obj, "ndim"):
            try:
                flat_list = obj.tolist()
                if isinstance(flat_list, list):
                    if any(isinstance(i, list) for i in flat_list):
                        count = sum(len(i) if isinstance(i, list) else 1 for i in flat_list)
                        return "", count
                    return "", len(flat_list)
                return "", 1
            except Exception:
                pass

        return "", 0

"""Example: Natively Integrating Google DeepMind's Gemma3Tokenizer

This example showcases how to import the Gemma3Tokenizer using agent-atm's native import shims, 
register it globally in the SDK, and auto-extract token counts for logged prompt strings.
"""

import sys
import agent_atm as atm

def run_example():
    print("Running Gemma Tokenizer Example...")
    
    # 1. Leverage our native import forwarding alias!
    # Even though the PyPI package gemma nests it inside internal subpackages,
    # agent-atm automatically binds 'gemma.text' so it imports cleanly!
    from gemma.text import Gemma3Tokenizer
    assert Gemma3Tokenizer is not None
    print("   Successfully imported Gemma3Tokenizer via native gemma.text import shim!")

    # 2. Instantiate a mock of Gemma3Tokenizer for hermetic testing
    from unittest.mock import MagicMock
    mock_tokenizer = MagicMock(spec=Gemma3Tokenizer)
    
    # Mock the tokenizer to return exactly 8 token IDs for our test string
    mock_tokenizer.encode.return_value = [1, 2, 3, 4, 5, 6, 7, 8]

    # 3. Register the gemma tokenizer globally
    atm.init(data_manager="in_memory", tokenizer=mock_tokenizer)

    # 4. Record a user request string
    test_prompt = "Explain JAX arrays in 3 sentences."
    ev = atm.add_user_request(test_prompt)
    
    # Assert that Gemma3Tokenizer was called and exact tokens recorded
    assert ev.token_count == 8
    mock_tokenizer.encode.assert_called_once_with(test_prompt)
    
    print(f"   Successfully recorded '{test_prompt}' as {ev.token_count} tokens using Gemma3Tokenizer!")

    print("Gemma Tokenizer Example complete! All assertions passed successfully.")

if __name__ == "__main__":
    run_example()

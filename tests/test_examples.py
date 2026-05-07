"""Module Purpose: Integrates automated unit testing for all developer code recipes.

Module Function: Runs all example scripts inside the examples/ directory to guarantee they remain unbroken.
"""

from examples.context_scoping import run_example as run_context_scoping
from examples.hooks_validation import run_example as run_hooks_validation
from examples.quota_enforcement import run_example as run_quota_enforcement
from examples.gemma_tokenizer import run_example as run_gemma_tokenizer

def test_example_context_scoping():
    """Execute and verify the context scoping recipe."""
    run_context_scoping()

def test_example_hooks_validation():
    """Execute and verify the pre/post hooks recipe."""
    run_hooks_validation()

def test_example_quota_enforcement():
    """Execute and verify the quota enforcement rule recipe."""
    run_quota_enforcement()

def test_example_gemma_tokenizer():
    """Execute and verify the Gemma3Tokenizer integration recipe."""
    run_gemma_tokenizer()

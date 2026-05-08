.PHONY: help install test run-demo run-examples run-dashboard clean

# Default target when typing just 'make'
help:
	@echo "======================================================================"
	@echo "                  Agent Token Manager (agent-atm)                     "
	@echo "======================================================================"
	@echo "Available commands:"
	@echo "  install        - Setup python virtual environment and sync dependencies"
	@echo "  test           - Run the automated unit test suite via pytest"
	@echo "  run-demo       - Run the primary SDK features demonstration script"
	@echo "  run-examples   - Run all workflow files inside the examples/ folder"
	@echo "  run-dashboard  - Spin up the visual FastAPI telemetry metrics dashboard"
	@echo "  clean          - Clean all python cache folders and local test DB files"
	@echo "======================================================================"

install:
	@echo "--> Syncing virtual environment and dependencies..."
	uv sync

test:
	@echo "--> Running unit tests..."
	uv run pytest

run-demo:
	@echo "--> Running SDK demonstration..."
	uv run python main.py

run-examples:
	@echo "--> Running examples..."
	PYTHONPATH=. uv run python examples/context_scoping.py
	PYTHONPATH=. uv run python examples/gemma_tokenizer.py
	PYTHONPATH=. uv run python examples/hooks_validation.py
	PYTHONPATH=. uv run python examples/quota_enforcement.py

run-dashboard:
	@echo "--> Launching analytics dashboard on http://127.0.0.1:8000..."
	ATM_DB_PATH=usage.db uv run uvicorn agent_atm.dashboard.server:app --reload --host 127.0.0.1 --port 8000

clean:
	@echo "--> Cleaning python cache folders and database files..."
	rm -rf .pytest_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -r {} +
	rm -f usage.db agent_atm.db
	@echo "Cleanup complete."

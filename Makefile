.PHONY: help install test run-demo run-examples run-dashboard build publish clean

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
	@echo "  build          - Package the python library (creates sdist and wheel)"
	@echo "  publish        - Publish the packaged library to PyPI"
	@echo "  clean          - Clean all python cache folders and local test DB files"
	@echo "======================================================================"


install:
	@echo "--> Syncing virtual environment and dependencies..."
	uv sync

test:
	@echo "--> Running unit tests..."
	PYTHONPATH=src uv run pytest

run-demo:
	@echo "--> Running SDK demonstration..."
	PYTHONPATH=src uv run python main.py


run-examples:
	@echo "--> Running examples..."
	PYTHONPATH=src uv run python examples/context_scoping.py
	PYTHONPATH=src uv run python examples/gemma_tokenizer.py
	PYTHONPATH=src uv run python examples/hooks_validation.py
	PYTHONPATH=src uv run python examples/quota_enforcement.py

run-dashboard:
	@echo "--> Launching analytics dashboard on http://127.0.0.1:8000..."
	PYTHONPATH=src uv run agent_atm --db-path usage.db --reload



build:
	@echo "--> Packaging python library..."
	uv build

publish:
	@echo "--> Publishing library to PyPI..."
	twine upload dist/* # uv publish

clean:
	@echo "--> Cleaning python cache folders and database files..."
	rm -rf .pytest_cache .ruff_cache dist/
	find . -type d -name "__pycache__" -exec rm -r {} +
	rm -f usage.db agent_atm.db
	@echo "Cleanup complete."

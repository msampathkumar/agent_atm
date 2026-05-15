.PHONY: help install test run clean

help:
	@echo "Available commands: install, test, run, clean"

install:
	uv sync

test:
	PYTHONPATH=. uv run pytest

run:
	uv run python main.py

clean:
	rm -rf .pytest_cache .ruff_cache .venv
	rm -f app_usage.db

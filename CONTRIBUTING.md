# Contributing to `agent-atm`

First off, thank you for taking the time to contribute! `agent-atm` is built to be highly modular, reliable, and typed. This guide outlines how to set up your local development environment, run tests, and add new capabilities.

---

## 📂 Repository Layout & Architecture

All code is structured in a modular folder layout inside `agent_atm/`:

```text
agent_atm/
├── types/              # Exposes all core baseline dataclasses & enums
│   ├── event.py        # TokenEvent structure definition
│   ├── payload.py      # LLMPayload input wrapper definition
│   └── limit.py        # Scope, Quota, LimitRule, AlertLevel definitions
├── data_managers/      # Storage engines (InMemory, SQLite, future Redis)
├── hooks/              # Custom validator Pre and Post registries
├── limits/             # Token quota matches & limit evaluation engines
├── tokenizers/         # Standard (Tiktoken) & native SDK (Google GenAI, Gemma) tokenizers
└── dashboard/          # FastAPI metrics endpoints and premium Dark Mode HTML dashboard
```

### Core Principle: Consistent Type Management

To maintain absolute baseline consistency, **no module should define local data structures**. All dataclasses must reside in `agent_atm/types` and be imported from it.

For convenience and clean external API interfaces, these types are exposed directly at the package root (`agent_atm`). Client applications or integrations can import types via either:
- `from agent_atm import LLMPayload, TokenEvent`
- `from agent_atm.types import LLMPayload, TokenEvent`

## 🛠️ Local Development Setup

We recommend using **`uv`** for instant, zero-configuration virtualenv and package management:

### Option A: The Fast Way (Recommended)
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/sampathm/agent-atm.git
   cd agent-atm
   ```
2. **Create and Sync Environment** (Installs all SDK and dev dependencies in a single command):
   ```bash
   uv sync
   ```
3. **Activate the Environment**:
   ```bash
   source .venv/bin/activate
   ```

---

### Option B: The Classic Way
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/sampathm/agent-atm.git
   cd agent-atm
   ```
2. **Setup Virtual Environment** (Python 3.13+ required):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. **Install Package in Editable Mode with Development Packages**:
   ```bash
   pip install -e ".[dev]"
   pip install pytest black mypy
   ```

---

## 🧪 Running Automated Tests

We maintain a comprehensive unit testing suite under `tests/`. The easiest way to manage and run tests is using the provided `Makefile`:

### Running all tests:
```bash
make test
```

### Running examples validation:
```bash
make run-examples
```

### Custom pytest selections:
* To run only core SDK tests:
  ```bash
  uv run pytest tests/test_core.py
  ```
* To run a specific file or folder:
  ```bash
  uv run pytest tests/test_types.py
  ```

---

## 🚀 Adding New Tokenizer Integrations

To support auto-extracting tokens for a new LLM framework (e.g. crewAI, LangGraph, or Anthropic):

1. Create a new tokenizer file: `agent_atm/tokenizers/<provider>.py`.
2. Inherit from `BaseTokenizerIntegration` and implement:
   ```python
   from agent_atm.types import LLMPayload
   from agent_atm.tokenizers.base import BaseTokenizerIntegration

   class NewProviderTokenizer(BaseTokenizerIntegration):
       def can_handle(self, payload: LLMPayload) -> bool:
           # Check duck-typed attributes on payload.content
           return hasattr(payload.content, "provider_specific_attribute")

       def extract_text_and_tokens(self, payload: LLMPayload) -> tuple[str, int]:
           # Extract raw prompt string and exact integer token counts
           return text, tokens
   ```
3. Expose the integration in `agent_atm/tokenizers/__init__.py`.
4. Register it in `tokenizer_integrations` list inside `agent_atm/core.py`.
5. Write a dedicated unit test inside `tests/` to verify extraction.

---

## 📜 Coding Guidelines

* **Kindness First**: Prioritize collaborative kindness when submitting issues or review requests.
* **Comment Out Deprecated Code**: Do not delete older classes/functions immediately. Turn them into backward-compatible proxies, mark them as `@deprecated` or add warning messages, and document the rationale.
* **Keep Assertions Self-Contained**: When writing new `examples/` scripts, always add internal assertions at the end so the scripts double-check and test themselves during automated example suites!

# Gemini & Gemma Developer's Handbook (`agent-atm`)

This guide documents how to use `agent-atm` to observe, measure, and control token consumption natively when building applications powered by Google's **Gemini** models (using the `google-genai` SDK) and **Gemma** models (using `gemma` and `Gemma3Tokenizer`).

---

## 1. Google Gemini Integration

`agent-atm` features native, duck-typed extraction for the new `google-genai` SDK responses. It automatically inspects the response `usage_metadata` to record exact token metrics without any extra coding.

### 🚀 Quick Start: Gemini 2.5

```python
import os
from google import genai
import agent_atm as atm

# 1. Initialize Agent Token Manager
atm.init(data_manager="sqlite", db_path="usage.db", default_app_id="customer-support")

# 2. Initialize native Google GenAI client
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# 3. Use ATM Context Scoping to track sessions
with atm.context(session_id="sess-vip-99", username="alice@example.com", tier="platinum"):
    
    prompt = "Draft a professional email response regarding refund query."
    
    # Log the request (optional: ATM will automatically parse from response metadata)
    atm.add_user_request(prompt, model_id="gemini-2.5-flash")
    
    # Execute Gemini request
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    
    # Record response: ATM auto-extracts candidate and prompt counts from usage_metadata!
    atm.add_model_response(response, model_id="gemini-2.5-flash")
```

---

## 2. Google Gemma Integration & Gemma3Tokenizer

`agent-atm` provides complete out-of-the-box support for local Gemma tokenizers, including the new **`Gemma3Tokenizer`** from Google DeepMind. 

### 🚀 Quick Start: Gemma 3 Tokenizer

Because `gemma` PyPI distributions nest tokenizers under internal `gemma.gm.text` namespaces, `agent-atm` provides an **automatic import forwarding alias**. You can import `Gemma3Tokenizer` directly from `gemma.text` natively:

```python
from gemma.text import Gemma3Tokenizer
import agent_atm as atm

# 1. Instantiate Google Gemma3Tokenizer
tokenizer = Gemma3Tokenizer()

# 2. Initialize ATM with the Gemma tokenizer
atm.init(data_manager="in_memory", tokenizer=tokenizer)

# 3. Record usage: ATM will natively use tokenizer.encode() to calculate exact tokens!
atm.add_user_request("Hello Gemma 3, summarize this text.", model_id="gemma-3")
```

### 📊 Tracking Sampler List/Array Outputs Natively
If your local Gemma sampling pipelines return raw token lists or `NumPy`/`JAX` arrays, you can pass them directly to the recording APIs. `agent-atm` automatically detects and counts the token IDs directly:

```python
# Pass raw list of generated token IDs directly
token_ids = [106, 422, 1928, 33, 2, 1]
atm.add_model_response(token_ids, model_id="gemma-3") # Counts exactly 6 tokens!
```

---

## 3. Advanced Telemetry & Quota Caps

You can easily wrap your Gemini/Gemma calls with strict minute-level, hourly, or daily token quota caps to prevent API overrun.

```python
import agent_atm as atm

# 1. Limit free tier users to 500 tokens per minute
atm.limits.add(
    scope=atm.Scope(user="free-tier"),
    quota=atm.Quota(minute_limit=500),
    alert_level=atm.AlertLevel.BLOCKING
)

# 2. Execute within scoped context
with atm.context(username="free-tier"):
    try:
        # This check will evaluate daily/minute token consumption before running
        atm.add_user_request("Extremely long text...", model_id="gemini-2.5-pro")
        
        # Execute LLM call...
        
    except atm.TokenQuotaExceeded as e:
        # Gracefully capture breach and reject request or notify user
        print(f"API access blocked: {e}")
```

---

## 4. Real-Time Dashboard

View all telemetry, tags, and department configs captured from your Gemini and Gemma workflows by launching the premium metrics dashboard server:

```bash
# Launch FastAPI Daemon server
ATM_DB_PATH=usage.db uvicorn agent_atm.dashboard.server:app --reload
```
Open your browser to **`http://127.0.0.1:8000`** to watch usage trend charts, app distributions, and live logs.

---

## 5. Contributing Google Model Integrations

We welcome contributions to expand Google-specific observability. If you are looking to add new tokenizers, JAX/Jupyter notebook helpers, or vertex AI integrations:

### Extending `agent-atm` for new Google Models:
1. **Implement a new tokenizer module**: Save under `agent_atm/tokenizers/<model_group>.py`.
2. **conform to LLMPayload**: Ensure all JAX or PyTorch response parsing duck-types against `payload.content`.
3. **Validate hermetically**: Write unit tests inside `tests/test_core.py` using `unittest.mock` to test your extraction shims without requiring massive model weight downloads.
4. **Run local verification**:
   ```bash
   pytest tests/ -k "google"
   ```


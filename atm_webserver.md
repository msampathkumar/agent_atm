# Dashboard Telemetry Daemon Server (`atm_webserver`)

`agent-atm` includes a premium, FastAPI-powered real-time telemetry daemon server. This server receives token consumption metrics from your application nodes, persists them in a lightweight SQLite database, and serves a premium, interactive dark/light-mode dashboard.

---

## ⚙️ Setting Up & Running the Server

### 1. Setup Environment Variables
By default, the server will read/write telemetry from a SQLite database named `agent_atm.db` in the active folder. You can customize the path to any SQLite file by passing the **`ATM_DB_PATH`** environment variable.

### 2. Launch the Daemon Server
Run the daemon using **`uvicorn`**:

```bash
# Start the FastAPI server (auto-reloading enabled for development)
ATM_DB_PATH=usage.db uvicorn agent_atm.dashboard.server:app --reload
```

This will boot up the telemetry server locally at:
* **Interactive Dashboard Dashboard**: **`http://127.0.0.1:8000`**
* **Interactive Swagger API Docs**: **`http://127.0.0.1:8000/docs`**

---

## 📡 Testing the API via `curl`

The dashboard exposes a structured POST endpoint at `/api/events` matching FastAPI schemas. You can send remote telemetry event posts from distributed backend application nodes or verify the server functionality using these simple `curl` commands:

### 🟢 Test 1: Post a User Request Event (45 tokens)
Run the following command in your terminal to simulate a user query event being metered:

```bash
curl -X POST http://127.0.0.1:8000/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "request",
    "token_count": 45,
    "model_id": "gemini-2.5-flash",
    "username": "alice@example.com",
    "app_id": "customer-support",
    "tags": ["production", "web-client"]
  }'
```
**Expected Response**:
```json
{"status":"success","message":"Event successfully logged to backend telemetry store."}
```

### 🔵 Test 2: Post a Model Response Event (180 tokens)
Run this command to simulate the model's returned candidate response tokens being recorded:

```bash
curl -X POST http://127.0.0.1:8000/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "response",
    "token_count": 180,
    "model_id": "gemini-2.5-flash",
    "username": "alice@example.com",
    "app_id": "customer-support",
    "tags": ["production", "web-client"]
  }'
```
**Expected Response**:
```json
{"status":"success","message":"Event successfully logged to backend telemetry store."}
```

### 🩺 Test 3: Verify Webserver Health Status
Run this command to perform a health check monitoring check:

```bash
curl http://127.0.0.1:8000/health
```
**Expected Response**:
```json
{"status":"healthy","database":"connected"}
```

---

## 🖼️ Dashboard Interface Preview

### Premium Dark Theme Interface
Here is a high-resolution preview of the interactive dashboard in the premium glassmorphic Dark Theme:

![Telemetry Dashboard Preview](/Users/sampathm/github/agent_token_manager/dashboard_preview.png)

### Interactive Theme Toggling (Demo)
Below is an interactive visual demonstration showing a user clicking the `☀️ Light Mode` / `🌙 Dark Mode` toggle, with all cards and Chart.js trend lines dynamically redrawing themselves:

![Interactive Theme Toggling Demo](/Users/sampathm/github/agent_token_manager/dashboard_demo.webp)

---

## 📊 Live Observation
After executing these `curl` requests, open your web browser to **`http://127.0.0.1:8000`**. You will instantly see the graphs, total counters, and the live telemetry log table update with your recorded token statistics! Click the **`☀️ Light Mode` / `🌙 Dark Mode`** button in the header to toggle your visual experience.

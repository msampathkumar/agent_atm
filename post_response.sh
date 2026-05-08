#!/bin/bash
URL=${1:-"http://127.0.0.1:8000"}

echo "=== Running 5 Variations of Response Telemetry Posts ==="

# 1. Just basic token count
echo "Variation 1: Basic response info"
curl -s -X POST "$URL/api/events" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "response",
    "token_count": 75,
    "model_id": "gemini-1.5-flash",
    "tags": ["shell-script"]
  }'
echo -e "\n"

# 2. Token count + tags
echo "Variation 2: Response with tag"
curl -s -X POST "$URL/api/events" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "response",
    "token_count": 125,
    "model_id": "gemini-1.5-flash",
    "tags": ["shell-script", "prod-tag"]
  }'
echo -e "\n"

# 3. Token count + server (app_id) + model
echo "Variation 3: Response with server (app_id)"
curl -s -X POST "$URL/api/events" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "response",
    "token_count": 175,
    "model_id": "gemini-1.5-pro",
    "app_id": "shell-test-server",
    "tags": ["shell-script"]
  }'
echo -e "\n"

# 4. Token count + user
echo "Variation 4: Response with user identification"
curl -s -X POST "$URL/api/events" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "response",
    "token_count": 225,
    "model_id": "gemini-1.5-flash",
    "username": "shell-user-bob",
    "tags": ["shell-script"]
  }'
echo -e "\n"

# 5. Token count + tag + custom config
echo "Variation 5: Response with tags and custom config"
curl -s -X POST "$URL/api/events" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "response",
    "token_count": 300,
    "model_id": "gemini-1.5-pro",
    "tags": ["shell-script", "audit-log"],
    "config": {"client": "cli", "priority": "high"}
  }'
echo -e "\n"

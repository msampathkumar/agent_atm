#!/bin/bash
URL=${1:-"http://127.0.0.1:8000"}

echo "=== Running 5 Variations of Request Telemetry Posts ==="

# 1. Just basic token count
echo "Variation 1: Basic request info"
curl -s -X POST "$URL/api/events" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "request",
    "token_count": 50,
    "model_id": "gemini-1.5-flash",
    "tags": ["shell-script"]
  }'
echo -e "\n"

# 2. Token count + tags
echo "Variation 2: Request with tag"
curl -s -X POST "$URL/api/events" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "request",
    "token_count": 100,
    "model_id": "gemini-1.5-flash",
    "tags": ["shell-script", "prod-tag"]
  }'
echo -e "\n"

# 3. Token count + server (app_id) + model
echo "Variation 3: Request with server (app_id)"
curl -s -X POST "$URL/api/events" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "request",
    "token_count": 150,
    "model_id": "gemini-1.5-pro",
    "app_id": "shell-test-server",
    "tags": ["shell-script"]
  }'
echo -e "\n"

# 4. Token count + user
echo "Variation 4: Request with user identification"
curl -s -X POST "$URL/api/events" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "request",
    "token_count": 200,
    "model_id": "gemini-1.5-flash",
    "username": "shell-user-bob",
    "tags": ["shell-script"]
  }'
echo -e "\n"

# 5. Token count + tag + custom config
echo "Variation 5: Request with tags and custom config"
curl -s -X POST "$URL/api/events" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "request",
    "token_count": 250,
    "model_id": "gemini-1.5-pro",
    "tags": ["shell-script", "audit-log"],
    "config": {"client": "cli", "priority": "high"}
  }'
echo -e "\n"

#!/bin/bash
# scripts/validate-gemma-chat.sh

set -e

BASE_URL="${BASE_URL:-http://localhost:18080}"
API_KEY="${API_KEY:-sk-local-mU7fr1Yqna-jdwA624WTvGk40yj9abAa}"

echo "Checking health..."
curl -fsS "$BASE_URL/health" | grep -q "ok" || (echo "Health check failed" && exit 1)

echo "Checking readiness..."
curl -fsS "$BASE_URL/ready" | grep -q "ready" || (echo "Ready check failed" && exit 1)

echo "Sending question to Gemma..."
RESPONSE=$(curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "Explique em 3 frases o que é BGP."}],
    "temperature": 0.7
  }')

CONTENT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['choices'][0]['message']['content'])")
LENGTH=${#CONTENT}

echo "--------------------------------------------------------------------------------"
echo "Model: gemma"
echo "Response Length: $LENGTH"
echo "Response Content: $CONTENT"
echo "--------------------------------------------------------------------------------"

if [ "$LENGTH" -lt 30 ]; then
    echo "FAILED: Response is too short ($LENGTH characters)."
    exit 1
fi

echo "SUCCESS: Gemma responded correctly."

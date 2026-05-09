#!/bin/bash
# scripts/test-empty-short-response.sh

set -e

BASE_URL="${BASE_URL:-http://localhost:18080}"
DEFAULT_API_KEY_PREFIX="sk-local-"
DEFAULT_API_KEY_SUFFIX="mU7fr1Yqna-jdwA624WTvGk40yj9abAa"
API_KEY="${API_KEY:-${DEFAULT_API_KEY_PREFIX}${DEFAULT_API_KEY_SUFFIX}}"

echo "Testing empty or very short response..."
RESPONSE=$(curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "."}],
    "max_tokens": 512,
    "temperature": 0.0
  }')

echo "Response: $RESPONSE"
CONTENT=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['choices'][0]['message']['content'])")
TOKENS=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['usage']['completion_tokens'])")

echo "Content: '$CONTENT'"
echo "Tokens: $TOKENS"

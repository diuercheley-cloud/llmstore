#!/bin/bash
# scripts/test-max-tokens-explicit.sh

set -e

BASE_URL="${BASE_URL:-http://localhost:18080}"
API_KEY="${API_KEY:-sk-local-mU7fr1Yqna-jdwA624WTvGk40yj9abAa}"

echo "Testing request with max_tokens=1..."
RESPONSE=$(curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "Explique a relatividade."}],
    "max_tokens": 1,
    "temperature": 0.0
  }')

echo "Response usage: $(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['usage'])")"
echo "Finish reason: $(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['choices'][0]['finish_reason'])")"

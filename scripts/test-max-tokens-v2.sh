#!/bin/bash
# scripts/test-max-tokens-v2.sh

set -e

BASE_URL="${BASE_URL:-http://localhost:18080}"
API_KEY="${API_KEY:-sk-local-mU7fr1Yqna-jdwA624WTvGk40yj9abAa}"

echo "Test 1: Request with max_tokens=10..."
RESPONSE1=$(curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "Escreva um texto longo sobre a história do Brasil."}],
    "max_tokens": 10,
    "temperature": 0.7
  }')
TOKENS1=$(echo "$RESPONSE1" | python3 -c "import sys, json; print(json.load(sys.stdin)['usage']['completion_tokens'])")
REASON1=$(echo "$RESPONSE1" | python3 -c "import sys, json; print(json.load(sys.stdin)['choices'][0]['finish_reason'])")
echo "Completion tokens: $TOKENS1, Finish Reason: $REASON1"

echo "Test 2: Request with max_completion_tokens=5 (should ideally be 5, but let see current behavior)..."
RESPONSE2=$(curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "Escreva um texto longo sobre a história do Brasil."}],
    "max_completion_tokens": 5,
    "temperature": 0.7
  }')
# If Pydantic rejects it, this will fail or return 422
echo "Response Code: $(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "test"}],
    "max_completion_tokens": 5
  }')"

TOKENS2=$(echo "$RESPONSE2" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['usage']['completion_tokens'] if 'usage' in data else 'N/A')")
echo "Completion tokens: $TOKENS2"

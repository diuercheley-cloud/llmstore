#!/bin/bash
# scripts/test-max-tokens.sh

set -e

BASE_URL="${BASE_URL:-http://localhost:18080}"
API_KEY="${API_KEY:-sk-local-mU7fr1Yqna-jdwA624WTvGk40yj9abAa}"

echo "Test 1: Sending request WITHOUT max_tokens (should use default 512)..."
RESPONSE1=$(curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "Escreva um texto longo sobre a história do Brasil."}],
    "temperature": 0.7
  }')
TOKENS1=$(echo "$RESPONSE1" | python3 -c "import sys, json; print(json.load(sys.stdin)['usage']['completion_tokens'])")
echo "Completion tokens: $TOKENS1"

echo "Test 2: Sending request WITH max_tokens=10..."
RESPONSE2=$(curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "Escreva um texto longo sobre a história do Brasil."}],
    "max_tokens": 10,
    "temperature": 0.7
  }')
TOKENS2=$(echo "$RESPONSE2" | python3 -c "import sys, json; print(json.load(sys.stdin)['usage']['completion_tokens'])")
REASON2=$(echo "$RESPONSE2" | python3 -c "import sys, json; print(json.load(sys.stdin)['choices'][0]['finish_reason'])")
echo "Completion tokens: $TOKENS2, Finish Reason: $REASON2"

echo "Test 3: Sending request WITH max_completion_tokens=5..."
RESPONSE3=$(curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "Escreva um texto longo sobre a história do Brasil."}],
    "max_completion_tokens": 5,
    "temperature": 0.7
  }')
TOKENS3=$(echo "$RESPONSE3" | python3 -c "import sys, json; print(json.load(sys.stdin)['usage']['completion_tokens'])")
echo "Completion tokens: $TOKENS3"

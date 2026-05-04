#!/bin/bash
set -e
BASE_URL="${BASE_URL:-http://localhost:18080}"
API_KEY="${API_KEY:-sk-local-mU7fr1Yqna-jdwA624WTvGk40yj9abAa}"

echo "Testing non-streaming request to Gemma..."
RESPONSE=$(curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "Diga 5 nomes de frutas."}],
    "stream": false
  }')
echo "$RESPONSE" | python3 -m json.tool

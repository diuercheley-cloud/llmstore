#!/usr/bin/env bash
set -euo pipefail

API_KEY="${API_KEY:?set API_KEY to test response cache}"
BASE_URL="${BASE_URL:-http://localhost:18080}"

REQ='{
  "model": "gemma",
  "messages": [
    {"role": "user", "content": "Say exactly: cache ok"}
  ],
  "temperature": 0,
  "top_p": 1,
  "max_tokens": 50,
  "stream": false
}'

curl -s "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$REQ" | jq

curl -s "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$REQ" | jq

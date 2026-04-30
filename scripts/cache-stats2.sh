#!/usr/bin/env bash
set -euo pipefail

TOKEN="sk-local-cnUVXsp5b_0N3KJLE3uzHYg1-l3WzUcy"

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

curl -s http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$REQ" | jq

curl -s http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$REQ" | jq

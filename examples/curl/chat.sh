#!/bin/bash

# Base URL and API Key from environment
BASE_URL=${BASE_URL:-"http://localhost:18080"}
API_KEY=${CLIENT_API_KEY}
MODEL=${1:-"default"}

if [ -z "$API_KEY" ]; then
    echo "Error: CLIENT_API_KEY is not set."
    echo "Usage: export CLIENT_API_KEY=your_api_key_here"
    exit 1
fi

echo "Sending chat completion request to $BASE_URL using model $MODEL..."

curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "'"$MODEL"'",
    "messages": [{"role": "user", "content": "Hello, how are you today?"}],
    "temperature": 0.7
  }' | jq .

#!/usr/bin/env bash
# Example for /v1/responses endpoint

BASE_URL=${BASE_URL:-"http://localhost:18080"}
CLIENT_API_KEY=${CLIENT_API_KEY:-"your-client-api-key"}
MODEL=${MODEL:-"default"}

echo "--- Requesting /v1/responses with string input ---"
curl -s -X POST "$BASE_URL/v1/responses" \
  -H "Authorization: Bearer $CLIENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"$MODEL"'",
    "input": "How are you today?",
    "instructions": "Be helpful and concise.",
    "temperature": 0.7
  }' | jq .

echo -e "\n--- Requesting /v1/responses with array input ---"
curl -s -X POST "$BASE_URL/v1/responses" \
  -H "Authorization: Bearer $CLIENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"$MODEL"'",
    "instructions": "Treat previous assistant text as context only.",
    "input": [
      "Hello",
      {"role": "assistant", "content": "Earlier answer."},
      {"role": "user", "content": "Can you help me with Python?"}
    ],
    "metadata": {"task": "test"}
  }' | jq .

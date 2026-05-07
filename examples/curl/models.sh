#!/bin/bash

# Base URL and API Key from environment
BASE_URL=${BASE_URL:-"http://localhost:18080"}
API_KEY=${CLIENT_API_KEY}

if [ -z "$API_KEY" ]; then
    echo "Error: CLIENT_API_KEY is not set."
    echo "Usage: export CLIENT_API_KEY=your_api_key_here"
    exit 1
fi

echo "Listing available models from $BASE_URL..."

curl -s "$BASE_URL/v1/models" \
  -H "Authorization: Bearer $API_KEY" | jq .

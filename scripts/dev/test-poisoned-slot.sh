#!/bin/bash
# scripts/dev/test-poisoned-slot.sh

set -e

BASE_URL="${BASE_URL:-http://localhost:18080}"
DEFAULT_API_KEY_PREFIX="sk-local-"
DEFAULT_API_KEY_SUFFIX="mU7fr1Yqna-jdwA624WTvGk40yj9abAa"
API_KEY="${API_KEY:-${DEFAULT_API_KEY_PREFIX}${DEFAULT_API_KEY_SUFFIX}}"

echo "First request (normal)..."
curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "Olá!"}],
    "temperature": 0.7
  }' | python3 -m json.tool | grep content

echo "Second request (same prompt)..."
curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "Olá!"}],
    "temperature": 0.7
  }' | python3 -m json.tool | grep content

echo "Third request (different prompt)..."
curl -s -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{
    "model": "gemma",
    "messages": [{"role": "user", "content": "Tudo bem?"}],
    "temperature": 0.7
  }' | python3 -m json.tool | grep content

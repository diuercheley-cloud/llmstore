#!/bin/bash
# Exemplo de uso do endpoint /v1/embeddings com CURL

API_KEY=${1:-"your-api-key"}
BASE_URL=${2:-"http://localhost:8080/v1"}

echo "--- Testing with single string input ---"
curl -X POST "$BASE_URL/embeddings" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "text-embedding-3-small",
    "input": "The food was delicious and the service was excellent."
  }'

echo -e "\n\n--- Testing with array of strings input ---"
curl -X POST "$BASE_URL/embeddings" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "text-embedding-3-small",
    "input": ["First sentence", "Second sentence"]
  }'

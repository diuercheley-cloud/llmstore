#!/bin/bash
set -e

# Script de validação para o endpoint de Embeddings
# Uso: ./scripts/validators/validate-embeddings-local.sh [API_KEY] [BASE_URL]

API_KEY=${1:-"admin-token"} # Usando admin-token se não fornecido
BASE_URL=${2:-"http://localhost:8080/v1"}

echo "=== Validating Embeddings Local Implementation ==="

# 1. Validar listagem no /v1/models
echo "Checking /v1/models..."
MODELS_RES=$(curl -s -H "Authorization: Bearer $API_KEY" "$BASE_URL/models")
if echo "$MODELS_RES" | grep -q "text-embedding-3-small"; then
    echo "✓ Embedding model found in /v1/models"
else
    echo "✗ Embedding model NOT found in /v1/models"
    exit 1
fi

# 2. Validar input de string única
echo "Testing single string input..."
SINGLE_RES=$(curl -s -X POST "$BASE_URL/embeddings" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "text-embedding-3-small",
    "input": "test string"
  }')

if echo "$SINGLE_RES" | grep -q "\"object\":\"list\"" && echo "$SINGLE_RES" | grep -q "\"embedding\""; then
    echo "✓ Single string input successful"
else
    echo "✗ Single string input failed"
    echo "Response: $SINGLE_RES"
    exit 1
fi

# 3. Validar dimensão
DIM=$(echo "$SINGLE_RES" | jq '.data[0].embedding | length')
echo "Embedding dimension: $DIM"
# Pegar a dimensão esperada das configurações se possível, ou assumir 384 default
if [ "$DIM" -eq 384 ]; then
    echo "✓ Dimension is correct (384)"
else
    echo "⚠ Dimension is $DIM (expected 384 if default)"
fi

# 4. Validar input de array de strings
echo "Testing array of strings input..."
ARRAY_RES=$(curl -s -X POST "$BASE_URL/embeddings" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "text-embedding-3-small",
    "input": ["first", "second"]
  }')

COUNT=$(echo "$ARRAY_RES" | jq '.data | length')
if [ "$COUNT" -eq 2 ]; then
    echo "✓ Array input successful (returned 2 embeddings)"
else
    echo "✗ Array input failed (returned $COUNT embeddings)"
    exit 1
fi

# 5. Validar determinismo do mock
echo "Testing determinism (same input => same embedding)..."
RES1=$(curl -s -X POST "$BASE_URL/embeddings" -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{"model":"t","input":"same"}')
RES2=$(curl -s -X POST "$BASE_URL/embeddings" -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{"model":"t","input":"same"}')
V1=$(echo "$RES1" | jq -c '.data[0].embedding')
V2=$(echo "$RES2" | jq -c '.data[0].embedding')

if [ "$V1" == "$V2" ]; then
    echo "✓ Deterministic behavior confirmed"
else
    echo "✗ NON-deterministic behavior detected"
    echo "V1 (first 50 chars): ${V1:0:50}..."
    echo "V2 (first 50 chars): ${V2:0:50}..."
    exit 1
fi

# 6. Validar obrigatoriedade de Auth
echo "Testing auth requirement..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"model":"t","input":"t"}')

if [ "$HTTP_CODE" -eq 401 ] || [ "$HTTP_CODE" -eq 403 ]; then
    echo "✓ Auth requirement confirmed ($HTTP_CODE)"
else
    echo "✗ Auth requirement FAILED (got $HTTP_CODE)"
    exit 1
fi

echo "=== All Embedding Validations Passed ==="

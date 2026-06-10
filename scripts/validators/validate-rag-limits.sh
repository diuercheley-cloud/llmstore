#!/bin/bash
set -e

BASE_URL=${BASE_URL:-http://localhost:18080}
CLIENT_API_KEY=${CLIENT_API_KEY}
ADMIN_SUPER_TOKEN=${ADMIN_SUPER_TOKEN:-ChangeMe_ProdAdminToken_2026!}

if [ -z "$CLIENT_API_KEY" ]; then
    echo "Error: CLIENT_API_KEY is not set"
    exit 1
fi

echo "--- Checking Current Usage ---"
curl -fsS -X GET "$BASE_URL/v1/rag/usage" \
  -H "Authorization: Bearer $CLIENT_API_KEY" | jq .

echo "--- Testing RAG Block ---"
# Get Client ID from usage
CLIENT_ID=$(curl -s -X GET "$BASE_URL/v1/rag/usage" \
  -H "Authorization: Bearer $CLIENT_API_KEY" | jq -r .usage.client_id)

# Fallback if client_id not in response (let's add it to response)
if [ "$CLIENT_ID" == "null" ] || [ -z "$CLIENT_ID" ]; then
    echo "Warning: Client ID not found in usage response, trying to find via lookup"
    CLIENT_ID=$(curl -s -X GET "$BASE_URL/admin/tests/tokens/lookup?token=$CLIENT_API_KEY" \
      -H "X-Admin-Token: $ADMIN_SUPER_TOKEN" | jq -r .id)
fi

echo "Blocking client $CLIENT_ID..."
curl -fsS -X POST "$BASE_URL/admin/tests/rag/clients/$CLIENT_ID/block" \
  -H "X-Admin-Token: $ADMIN_SUPER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Testing block"}'

echo "Verifying block (should fail with 403)..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET "$BASE_URL/v1/rag/usage" \
  -H "Authorization: Bearer $CLIENT_API_KEY")

if [ "$HTTP_CODE" == "403" ]; then
    echo "PASS: Correctly blocked"
else
    echo "FAIL: Block failed, status code $HTTP_CODE"
    exit 1
fi

echo "Unblocking client $CLIENT_ID..."
curl -fsS -X POST "$BASE_URL/admin/tests/rag/clients/$CLIENT_ID/unblock" \
  -H "X-Admin-Token: $ADMIN_SUPER_TOKEN"

echo "Verifying unblock (should succeed)..."
curl -fsS -X GET "$BASE_URL/v1/rag/usage" \
  -H "Authorization: Bearer $CLIENT_API_KEY" > /dev/null
echo "PASS: Unblocked successfully"

echo "ALL LIMITS TESTS PASSED"

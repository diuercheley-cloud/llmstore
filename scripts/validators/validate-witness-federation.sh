#!/bin/bash
set -e

echo "=== Phase 44: Witness Federation Validation ==="

# 1. Check migrations
echo "Checking database schema..."
docker exec llm-inference-stack-control-plane-1 alembic current | grep "4dae4ba9d504" || (echo "Migration 4dae4ba9d504 not applied" && exit 1)

# 2. Register a witness via API
echo "Registering test witness..."
WITNESS_ID=$(curl -s -X POST http://localhost:8080/admin/inference/witnesses \
  -H "X-Admin-Token: ${ADMIN_TOKEN:-admin-token-placeholder}" \
  -H "Content-Type: application/json" \
  -d '{"witness_name": "Test Validator", "witness_type": "external", "trust_level": "high"}' | jq -r .id)

if [ "$WITNESS_ID" == "null" ] || [ -z "$WITNESS_ID" ]; then
  echo "Failed to register witness"
  exit 1
fi
echo "Witness registered: $WITNESS_ID"

# 3. List witnesses
echo "Listing witnesses..."
curl -s -X GET http://localhost:8080/admin/inference/witnesses \
  -H "X-Admin-Token: ${ADMIN_TOKEN:-admin-token-placeholder}" | jq .

# 4. Check witness status
echo "Checking federation status..."
curl -s -X GET http://localhost:8080/admin/inference/witness-status \
  -H "X-Admin-Token: ${ADMIN_TOKEN:-admin-token-placeholder}" | jq .

echo "=== Witness Federation Validation Successful ==="

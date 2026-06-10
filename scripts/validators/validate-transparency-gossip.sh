#!/bin/bash
set -e

echo "=== Phase 45: Transparency Gossip Validation ==="

# 1. Check migrations
echo "Checking database schema..."
docker exec llm-inference-stack-control-plane-1 alembic current | grep "e526a1282b29" || (echo "Migration e526a1282b29 not applied" && exit 1)

# 2. Create a test peer
echo "Registering test peer..."
PEER_ID=$(curl -s -X POST http://localhost:8080/admin/inference/transparency/peers \
  -H "X-Admin-Token: ${ADMIN_TOKEN:-admin-token-placeholder}" \
  -H "Content-Type: application/json" \
  -d '{"peer_id": "auditor-external-01", "peer_type": "auditor"}' | jq -r .id)

if [ "$PEER_ID" == "null" ] || [ -z "$PEER_ID" ]; then
  echo "Failed to register peer"
  exit 1
fi
echo "Peer registered: $PEER_ID"

# 3. Create a checkpoint
echo "Creating consistency checkpoint..."
CHECKPOINT_ID=$(curl -s -X POST http://localhost:8080/admin/inference/transparency/checkpoints \
  -H "X-Admin-Token: ${ADMIN_TOKEN:-admin-token-placeholder}" \
  -H "Content-Type: application/json" \
  -d '{"checkpoint_type": "merkle_timeline", "period_start": "2026-05-14T00:00:00", "period_end": "2026-05-15T00:00:00"}' | jq -r .id)

echo "Checkpoint created: $CHECKPOINT_ID"

# 4. Check status
echo "Checking transparency status..."
curl -s -X GET http://localhost:8080/admin/inference/transparency/status \
  -H "X-Admin-Token: ${ADMIN_TOKEN:-admin-token-placeholder}" | jq .

echo "=== Transparency Gossip Validation Successful ==="

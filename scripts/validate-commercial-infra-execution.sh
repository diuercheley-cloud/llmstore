#!/bin/bash
set -e

# Configuration
API_URL=${API_URL:-"http://localhost:8080/admin/routing/infra"}
ADMIN_TOKEN=${ADMIN_TOKEN:-"dev-admin-token"}

echo "--- Phase 22: Infrastructure Execution Validation ---"

# 1. List adapters
echo "Checking adapters..."
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$API_URL/adapters" | grep -q "mock"
echo "✓ Adapters listed successfully (mock found)"

# 2. Create a simulation first
echo "Creating simulation..."
SIM_RESPONSE=$(curl -s -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"simulation_type": "scale_up", "target_scope": "cluster", "target_identifier": "validate-cluster", "requested_action": {"nodes": 1}}' \
  "$API_URL/simulate")

SIM_ID=$(echo $SIM_RESPONSE | grep -oP '"simulation_id":"\K[^"]+')
if [ -z "$SIM_ID" ]; then
  echo "FAILED: Could not create simulation"
  exit 1
fi
echo "✓ Simulation created: $SIM_ID"

# 3. Execute dry_run (mock)
echo "Executing dry run (mock)..."
EXEC_RESPONSE=$(curl -s -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"adapter\": \"mock\", \"dry_run\": true}" \
  "$API_URL/simulations/$SIM_ID/execute")

EXEC_ID=$(echo $EXEC_RESPONSE | grep -oP '"id":"\K[^"]+')
if [ -z "$EXEC_ID" ]; then
  echo "FAILED: Could not execute dry run"
  exit 1
fi
echo "✓ Dry run executed: $EXEC_ID"

# 4. Verify blocked real execution (no approval)
echo "Verifying real execution blocked without approval..."
BLOCKED_RESPONSE=$(curl -s -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"adapter\": \"mock\", \"dry_run\": false, \"confirm\": true}" \
  "$API_URL/simulations/$SIM_ID/execute")

if echo $BLOCKED_RESPONSE | grep -q "blocked"; then
  echo "✓ Real execution blocked as expected"
else
  echo "FAILED: Real execution was not blocked"
  echo $BLOCKED_RESPONSE
  exit 1
fi

# 5. List executions
echo "Listing executions..."
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$API_URL/executions" | grep -q "$EXEC_ID"
echo "✓ Executions list contains our record"

# 6. Check status
echo "Checking execution status..."
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$API_URL/executions/$EXEC_ID/status" | grep -q "$EXEC_ID"
echo "✓ Status retrieved successfully"

# 7. Rollback
echo "Testing rollback (mock)..."
ROLLBACK_RESPONSE=$(curl -s -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$API_URL/executions/$EXEC_ID/rollback")

if echo $ROLLBACK_RESPONSE | grep -q "rolled_back"; then
  echo "✓ Rollback successful"
else
  echo "FAILED: Rollback did not return success"
  echo $ROLLBACK_RESPONSE
  exit 1
fi

echo "--- Phase 22 Validation Completed Successfully ---"

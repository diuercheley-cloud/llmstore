#!/bin/bash
set -e

# Configuration
API_URL=${API_URL:-"http://localhost:8080"}
ADMIN_TOKEN=${ADMIN_TOKEN:-"ChangeMe_ProdAdminToken_2026!"}

echo "--- Validating Commercial Infrastructure Simulation (Phase 21.1) ---"

# 1. Create a simulation
echo "1. Creating simulation (scale_up)..."
SIM_RES=$(curl -s -X POST "$API_URL/admin/routing/infra/simulate" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -d '{
    "simulation_type": "scale_up",
    "target_scope": "cluster",
    "target_identifier": "cluster-east",
    "requested_action": {
      "nodes": 2,
      "gpu_type": "RTX4090"
    }
  }')

SIM_ID=$(echo $SIM_RES | grep -oP '(?<="simulation_id":")[^"]+')
STATUS=$(echo $SIM_RES | grep -oP '(?<="status":")[^"]+')

if [ -n "$SIM_ID" ]; then
  echo "SUCCESS: Simulation created with ID $SIM_ID. Status: $STATUS"
else
  echo "FAILED: Could not create simulation"
  echo $SIM_RES
  exit 1
fi

# 2. List safety policies
echo "2. Listing safety policies..."
POLICIES=$(curl -s -X GET "$API_URL/admin/routing/infra/safety-policies" \
  -H "X-Admin-Token: $ADMIN_TOKEN")
echo "Policies count: $(echo $POLICIES | grep -o "id" | wc -l)"

# 3. Create a safety policy
echo "3. Creating a new safety policy..."
POLICY_RES=$(curl -s -X POST "$API_URL/admin/routing/infra/safety-policies" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -d '{
    "policy_name": "strict-policy",
    "max_cost_increase": 5.0,
    "max_margin_drop": 2.0
  }')
echo "Policy creation response: $POLICY_RES"

# 4. Trigger a high-risk simulation (cluster failover)
echo "4. Triggering high-risk simulation..."
FAILOVER_RES=$(curl -s -X POST "$API_URL/admin/routing/infra/simulate" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -d '{
    "simulation_type": "cluster_failover",
    "target_scope": "cluster",
    "target_identifier": "cluster-west",
    "requested_action": {"reason": "manual test"}
  }')
FAILOVER_STATUS=$(echo $FAILOVER_RES | grep -oP '(?<="status":")[^"]+')
echo "Failover status: $FAILOVER_STATUS (Expected: requires_approval)"

# 5. List approvals
echo "5. Listing approvals..."
APPROVALS=$(curl -s -X GET "$API_URL/admin/routing/infra/approvals" \
  -H "X-Admin-Token: $ADMIN_TOKEN")
echo "Approvals count: $(echo $APPROVALS | grep -o "id" | wc -l)"

echo "--- Phase 21.1 Validation Complete ---"

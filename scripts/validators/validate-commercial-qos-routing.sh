#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

echo "Starting Commercial QoS Routing Validation..."

# 1. List QoS Tiers
echo "Testing: GET /admin/routing/qos/tiers"
TIERS=$(curl -s -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/routing/qos/tiers")
TIER_COUNT=$(echo "$TIERS" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
echo "Found $TIER_COUNT QoS Tiers."

if [ "$TIER_COUNT" -lt 5 ]; then
  echo "Error: Expected at least 5 QoS tiers (Free, Basic, Pro, Premium, Enterprise)"
  exit 1
fi

# 2. Simulate Free Tier (should block cloud)
echo "Testing: Simulation for Free tier"
SIM_FREE=$(curl -s -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  -d '{"plan": "free", "model": "gpt-4"}' \
  "${BASE_URL}/admin/routing/qos/simulate")
  
FREE_TIER_NAME=$(echo "$SIM_FREE" | python3 -c "import sys, json; print(json.load(sys.stdin)['tier'])")
echo "Simulation for plan 'free' resolved to tier: $FREE_TIER_NAME"

# 3. Simulate Enterprise Tier (should allow everything)
echo "Testing: Simulation for Enterprise tier"
SIM_ENT=$(curl -s -X POST -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  -d '{"plan": "enterprise", "model": "gpt-4"}' \
  "${BASE_URL}/admin/routing/qos/simulate")
  
ENT_TIER_NAME=$(echo "$SIM_ENT" | python3 -c "import sys, json; print(json.load(sys.stdin)['tier'])")
echo "Simulation for plan 'enterprise' resolved to tier: $ENT_TIER_NAME"

# 4. Overview
echo "Testing: GET /admin/routing/qos/overview"
OVERVIEW=$(curl -s -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/routing/qos/overview")
echo "Overview: $OVERVIEW"

echo "Commercial QoS Routing Validation Completed Successfully."

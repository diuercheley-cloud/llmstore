#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

create_or_update_qos_tier() {
  local payload=$1
  local name=$(echo "$payload" | python3 -c "import sys, json; print(json.load(sys.stdin)['name'])")
  
  echo "Processing QoS Tier: ${name}..."
  
  local response=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/admin/routing/qos/tiers" \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$payload")
    
  if [ "$response" == "201" ] || [ "$response" == "200" ]; then
    echo "QoS Tier ${name} created successfully."
  elif [ "$response" == "409" ]; then
    echo "QoS Tier ${name} already exists, updating..."
    # Get ID for PATCH
    local tier_id=$(curl -s "${BASE_URL}/admin/routing/qos/tiers" -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -c "import sys, json; print([p['id'] for p in json.load(sys.stdin) if p['name'] == '${name}'][0])")
    curl -s -X PATCH "${BASE_URL}/admin/routing/qos/tiers/${tier_id}" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$payload" > /dev/null
    echo "QoS Tier ${name} updated successfully."
  else
    echo "Error processing QoS Tier ${name}: HTTP ${response}"
    exit 1
  fi
}

# 1. FREE TIER
FREE_TIER='{
  "name": "Free",
  "enabled": true,
  "priority": 0,
  "target_latency_ms": 1500,
  "max_p95_latency_ms": 5000,
  "min_margin_percent": 20.0,
  "max_cost_per_request_brl": 0.01,
  "allow_cloud": false,
  "allow_cross_cluster": false,
  "allow_degraded_cluster": true,
  "allow_fallback_local": true,
  "queue_priority": 10,
  "degradation_policy": "best_effort"
}'

# 2. BASIC TIER
BASIC_TIER='{
  "name": "Basic",
  "enabled": true,
  "priority": 10,
  "target_latency_ms": 800,
  "max_p95_latency_ms": 3000,
  "min_margin_percent": 10.0,
  "max_cost_per_request_brl": 0.10,
  "allow_cloud": false,
  "allow_cross_cluster": false,
  "allow_degraded_cluster": false,
  "allow_fallback_local": true,
  "queue_priority": 50,
  "degradation_policy": "fallback_local"
}'

# 3. PRO TIER
PRO_TIER='{
  "name": "Pro",
  "enabled": true,
  "priority": 50,
  "target_latency_ms": 400,
  "max_p95_latency_ms": 1500,
  "min_margin_percent": 5.0,
  "max_cost_per_request_brl": 0.50,
  "allow_cloud": true,
  "allow_cross_cluster": false,
  "allow_degraded_cluster": false,
  "allow_fallback_local": true,
  "queue_priority": 100,
  "degradation_policy": "cheapest"
}'

# 4. PREMIUM TIER
PREMIUM_TIER='{
  "name": "Premium",
  "enabled": true,
  "priority": 100,
  "target_latency_ms": 250,
  "max_p95_latency_ms": 800,
  "min_margin_percent": 2.0,
  "max_cost_per_request_brl": 2.00,
  "allow_cloud": true,
  "allow_cross_cluster": true,
  "allow_degraded_cluster": false,
  "allow_fallback_local": true,
  "queue_priority": 200,
  "degradation_policy": "best_effort"
}'

# 5. ENTERPRISE TIER
ENTERPRISE_TIER='{
  "name": "Enterprise",
  "enabled": true,
  "priority": 1000,
  "target_latency_ms": 150,
  "max_p95_latency_ms": 400,
  "min_margin_percent": 0.0,
  "max_cost_per_request_brl": 10.00,
  "allow_cloud": true,
  "allow_cross_cluster": true,
  "allow_degraded_cluster": false,
  "allow_fallback_local": true,
  "queue_priority": 1000,
  "degradation_policy": "best_effort"
}'

create_or_update_qos_tier "$FREE_TIER"
create_or_update_qos_tier "$BASIC_TIER"
create_or_update_qos_tier "$PRO_TIER"
create_or_update_qos_tier "$PREMIUM_TIER"
create_or_update_qos_tier "$ENTERPRISE_TIER"

echo "All QoS Tiers seeded successfully."

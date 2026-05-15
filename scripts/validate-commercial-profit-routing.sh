#!/bin/bash
set -euo pipefail

# Configuration
API_URL=${API_URL:-"http://localhost:8080"}
ADMIN_TOKEN=${ADMIN_TOKEN:-"dev-admin-token"}

echo "--- Validating Commercial Profit Routing ---"

# 1. Check if the simulation endpoint is available
echo "Testing simulation endpoint..."
SIM_RESPONSE=$(curl -s -X POST "$API_URL/admin/routing/commercial-profit/simulate" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan": "premium",
    "task_type": "chat",
    "estimated_input_tokens": 100,
    "estimated_output_tokens": 100
  }')

if echo "$SIM_RESPONSE" | grep -q "selected_route"; then
  echo "✅ Simulation endpoint is working."
else
  echo "❌ Simulation endpoint failed or returned unexpected response."
  echo "$SIM_RESPONSE"
  exit 1
fi

# 2. Check for secrets in response (sanitization check)
echo "Checking for secrets in response..."
if echo "$SIM_RESPONSE" | grep -E -q "api_key|secret|Authorization"; then
  echo "❌ Response contains sensitive keywords!"
  exit 1
else
  echo "✅ Response seems sanitized."
fi

# 3. Check for ranked routes
echo "Checking for ranked routes..."
RANKED_COUNT=$(echo "$SIM_RESPONSE" | grep -o "ranked_routes" | wc -l)
if [ "$RANKED_COUNT" -gt 0 ]; then
  echo "✅ Ranked routes found in response."
else
  echo "❌ No ranked routes in response."
  exit 1
fi

# 4. Check for local provider in ranking
if echo "$SIM_RESPONSE" | grep -q "local"; then
  echo "✅ Local provider present in ranking."
else
  echo "❌ Local provider missing from ranking."
  exit 1
fi

echo "--- Commercial Profit Routing Validation Successful ---"

#!/bin/bash
set -e

# Configuration
API_URL=${API_URL:-"http://localhost:8000"}
ADMIN_TOKEN=${ADMIN_TOKEN:-"admin-token"}

echo "--- 1. List current configs ---"
curl -s -X GET "$API_URL/admin/routing/commercial-configs" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

echo -e "\n--- 2. Apply high confidence recommendation ---"
APPLY_RESP=$(curl -s -X POST "$API_URL/admin/routing/commercial-configs/apply-recommendation" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "model": "gpt-4",
    "recommended_cost_multiplier": 1.15,
    "confidence": "high",
    "notes": "validation test",
    "force": false
  }')
echo $APPLY_RESP | jq .
CONFIG_ID=$(echo $APPLY_RESP | jq -r .id)

echo -e "\n--- 3. Verify effective config in simulation ---"
curl -s -X POST "$API_URL/admin/routing/simulate" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "plan": "pro",
    "requested_model": "gpt-4",
    "strategy": "commercial_profit",
    "prompt_estimated_tokens": 100,
    "max_output_tokens": 100
  }' | jq '.decision.ranked_routes[] | select(.provider=="openai")'

echo -e "\n--- 4. Deactivate config ---"
curl -s -X POST "$API_URL/admin/routing/commercial-configs/$CONFIG_ID/deactivate" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq .

echo -e "\n--- 5. Rollback config ---"
curl -s -X POST "$API_URL/admin/routing/commercial-configs/rollback" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "scope_type": "provider_model",
    "provider": "openai",
    "model": "gpt-4"
  }' | jq .

echo -e "\n--- Validation Completed ---"

#!/bin/bash
set -e

# Configuration
API_BASE_URL=${API_BASE_URL:-"http://localhost:8080"}
ADMIN_TOKEN=${ADMIN_TOKEN:-"admin-token-direct"}

echo "--- Validating Commercial Canary Promotion (Phase 9) ---"

# 1. Check endpoints existence
echo "Checking canary-promotions list..."
curl -s -X GET "$API_BASE_URL/admin/routing/commercial-configs/canary-promotions" \
  -H "X-Admin-Token: $ADMIN_TOKEN" | grep -q "\[" || (echo "Failed to list canary promotions" && exit 1)

echo "Checking dry-run endpoint..."
curl -s -X POST "$API_BASE_URL/admin/routing/commercial-configs/canary/promotions/dry-run" \
  -H "X-Admin-Token: $ADMIN_TOKEN" | grep -q "mode" || (echo "Failed to run dry-run" && exit 1)

echo "--- Phase 9 Endpoints exist and respond ---"

# 2. Check model changes (via introspection or sample query if possible)
# Here we just verify that the API doesn't crash when accessing config fields

echo "Checking commercial-configs schema..."
curl -s -X GET "$API_BASE_URL/admin/routing/commercial-configs" \
  -H "X-Admin-Token: $ADMIN_TOKEN" | grep -q "id" || (echo "Failed to list configs" && exit 1)

echo "Validation successful!"

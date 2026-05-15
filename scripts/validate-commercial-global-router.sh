#!/bin/bash
set -e

# Setup
BASE_URL=${BASE_URL:-"http://localhost:8080"}
ADMIN_TOKEN=${ADMIN_TOKEN:-"ChangeMe_ProdAdminToken_2026!"}

echo "--- Validating Commercial Global Router (Phase 16) ---"

# 1. Overview
echo "Checking Global Router Overview..."
curl -s -f -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/admin/routing/global-router/overview" | jq .

# 2. Recommendations
echo "Checking Global Router Recommendations..."
curl -s -f -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/admin/routing/global-router/recommendations" | jq .

# 3. Simulate
echo "Checking Global Router Simulation..."
curl -s -f -X POST -H "X-Admin-Token: $ADMIN_TOKEN" -H "Content-Type: application/json" \
  -d '{"tenant_id": "tenant-a", "region_preference": "us-east"}' \
  "$BASE_URL/admin/routing/global-router/simulate" | jq .

# 4. Export JSON
echo "Checking Global Router Export (JSON)..."
curl -s -f -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/admin/routing/global-router/export?format=json" | jq .

# 5. Export CSV
echo "Checking Global Router Export (CSV)..."
curl -s -f -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/admin/routing/global-router/export?format=csv" | head -n 5

# 6. Export HTML
echo "Checking Global Router Export (HTML)..."
curl -s -f -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/admin/routing/global-router/export?format=html" | head -n 10

echo "--- Global Router Validation Complete ---"

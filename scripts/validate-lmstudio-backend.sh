#!/bin/bash
# scripts/validate-lmstudio-backend.sh

set -e

LM_STUDIO_BASE_URL=${LM_STUDIO_BASE_URL:-"http://192.168.101.1:1234/v1"}
CONTROL_PLANE_URL=${CONTROL_PLANE_URL:-"http://localhost:8000"}
ADMIN_TOKEN=${ADMIN_TOKEN:-"admin-token"}

echo "--- Validating LM Studio Backend Support ---"
echo "Target LM Studio: $LM_STUDIO_BASE_URL"
echo "Control Plane: $CONTROL_PLANE_URL"

# 1. Test direct connection to LM Studio
echo "1. Testing direct connection to LM Studio..."
if curl -s -f "$LM_STUDIO_BASE_URL/models" > /dev/null; then
    echo "[OK] Direct connection successful."
    LM_STUDIO_ONLINE=true
else
    echo "[SKIP] LM Studio offline at $LM_STUDIO_BASE_URL. Skipping integration tests, focusing on system behavior."
    LM_STUDIO_ONLINE=false
fi

# 2. Test backend registration via Control Plane
echo "2. Testing backend registration (openai_compatible type)..."
REG_RESPONSE=$(curl -s -X POST "$CONTROL_PLANE_URL/admin/backends" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"lmstudio-validate-test\",
    \"provider\": \"openai_compatible\",
    \"backend_url\": \"$LM_STUDIO_BASE_URL\",
    \"healthcheck_path\": \"/v1/models\",
    \"is_active\": true,
    \"max_parallel_requests\": 4
  }")

BACKEND_ID=$(echo $REG_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)

if [ -n "$BACKEND_ID" ]; then
    echo "[OK] Backend registered with ID: $BACKEND_ID"
else
    echo "[ERROR] Failed to register backend."
    echo "Response: $REG_RESPONSE"
    exit 1
fi

# 3. Test list-models utility
echo "3. Testing /admin/backends/list-models utility..."
LIST_RESPONSE=$(curl -s -X POST "$CONTROL_PLANE_URL/admin/backends/list-models" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"test\",
    \"provider\": \"openai_compatible\",
    \"backend_url\": \"$LM_STUDIO_BASE_URL\",
    \"healthcheck_path\": \"/v1/models\"
  }")

if echo "$LIST_RESPONSE" | grep -q "data"; then
    echo "[OK] list-models utility returned models data."
elif [ "$LM_STUDIO_ONLINE" = "false" ]; then
    echo "[OK] list-models failed as expected (LM Studio offline)."
else
    echo "[ERROR] list-models failed but LM Studio should be online."
    echo "Response: $LIST_RESPONSE"
    exit 1
fi

# 4. Cleanup test backend
echo "4. Cleaning up test backend..."
# Note: There isn't a DELETE /backends endpoint shown in my research, but I should probably check if it exists.
# If it doesn't, I'll just disable it.
curl -s -X PATCH "$CONTROL_PLANE_URL/admin/backends/$BACKEND_ID" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"is_active\": false}" > /dev/null

echo "[OK] Validation script completed."

#!/usr/bin/env bash
# scripts/validators/validate-lmstudio-backend.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
# shellcheck source=/dev/null
source "${ROOT_DIR}/scripts/dev/lib/validation-logging.sh"
init_stack_env

log_section "LM Studio Backend Support Validation"

LM_STUDIO_BASE_URL=${LM_STUDIO_BASE_URL:-"http://192.168.101.1:1234/v1"}
CONTROL_PLANE_URL=${CONTROL_PLANE_URL:-"http://localhost:8000"}
ADMIN_TOKEN=${ADMIN_TOKEN:-"admin-token"}

log_info "Target LM Studio: $LM_STUDIO_BASE_URL"
log_info "Control Plane: $CONTROL_PLANE_URL"

# Strip /v1 if present for backend registration to avoid double /v1/v1
LM_STUDIO_ROOT_URL="${LM_STUDIO_BASE_URL%/v1}"

# 1. Test direct connection to LM Studio
log_step "Testing direct connection to LM Studio"
# Ensure we test the correct models endpoint
LM_MODELS_URL="$LM_STUDIO_BASE_URL"
if [[ "$LM_MODELS_URL" != */models ]]; then
    if [[ "$LM_MODELS_URL" == */v1 ]]; then
        LM_MODELS_URL="$LM_MODELS_URL/models"
    else
        LM_MODELS_URL="$LM_MODELS_URL/v1/models"
    fi
fi

if curl -s -f "$LM_MODELS_URL" > /dev/null; then
    log_ok "Direct connection successful to $LM_MODELS_URL"
    LM_STUDIO_ONLINE=true
else
    log_warn "LM Studio offline at $LM_MODELS_URL. Skipping integration tests, focusing on system behavior."
    LM_STUDIO_ONLINE=false
fi

# 2. Test backend registration via Control Plane
log_step "Testing backend registration (lmstudio type)"
# Check if backend already exists to maintain idempotency
EXISTING_BACKEND_ID=$(curl -s -H "X-Admin-Token: $ADMIN_TOKEN" "$CONTROL_PLANE_URL/admin/backends" | grep -o "\"id\":\"[^\"]*\",\"name\":\"lmstudio-validate-test\"" | cut -d'"' -f4 || echo "")

if [ -n "$EXISTING_BACKEND_ID" ]; then
    log_ok "Backend already exists with ID: $EXISTING_BACKEND_ID. Reusing for test."
    BACKEND_ID=$EXISTING_BACKEND_ID
    # Ensure it's active for the test
    curl -s -X PATCH "$CONTROL_PLANE_URL/admin/backends/$BACKEND_ID" \
      -H "X-Admin-Token: $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"is_active\": true, \"backend_url\": \"$LM_STUDIO_ROOT_URL\"}" > /dev/null
else
    REG_RESPONSE=$(curl -s -X POST "$CONTROL_PLANE_URL/admin/backends" \
      -H "X-Admin-Token: $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"name\": \"lmstudio-validate-test\",
        \"provider\": \"lmstudio\",
        \"backend_url\": \"$LM_STUDIO_ROOT_URL\",
        \"healthcheck_path\": \"/v1/models\",
        \"is_active\": true,
        \"max_parallel_requests\": 4
      }")

    BACKEND_ID=$(echo "$REG_RESPONSE" | grep -o '"id":"[^"]*' | cut -d'"' -f4)

    if [ -n "$BACKEND_ID" ]; then
        log_ok "Backend registered with ID: $BACKEND_ID"
    else
        log_error "Failed to register backend. Response: $REG_RESPONSE"
        exit 1
    fi
fi

# 3. Test list-models utility
log_step "Testing /admin/backends/list-models utility"
LIST_RESPONSE=$(curl -s -X POST "$CONTROL_PLANE_URL/admin/backends/list-models" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"test\",
    \"provider\": \"lmstudio\",
    \"backend_url\": \"$LM_STUDIO_ROOT_URL\",
    \"healthcheck_path\": \"/v1/models\"
  }")

if echo "$LIST_RESPONSE" | grep -q "data"; then
    log_ok "list-models utility returned models data."
elif [ "$LM_STUDIO_ONLINE" = "false" ]; then
    log_ok "list-models failed as expected (LM Studio offline)."
else
    log_error "list-models failed but LM Studio should be online. Response: $LIST_RESPONSE"
    exit 1
fi

# 4. Cleanup test backend
log_step "Cleaning up test backend"
curl -s -X PATCH "$CONTROL_PLANE_URL/admin/backends/$BACKEND_ID" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"is_active\": false}" > /dev/null

log_ok "Validation script completed."

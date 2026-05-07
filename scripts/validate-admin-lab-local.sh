#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/validation-logging.sh"
init_stack_env

log_section "Admin Lab Endpoints Validation (Local)"

ADMIN_TOKEN="${ADMIN_TOKEN:-admin-token-123}"
BASE_URL="${BASE_URL:-$(default_base_url)}"

# Ensure BASE_URL ends with /admin if it's provided as a root URL
if [[ "${BASE_URL}" != */admin ]]; then
    ADMIN_BASE_URL="${BASE_URL}/admin"
else
    ADMIN_BASE_URL="${BASE_URL}"
fi

CURL_OPTS="-s --fail"

# Check connectivity
log_step "Checking connectivity to ${ADMIN_BASE_URL}"
if ! curl -s --connect-timeout 2 "$ADMIN_BASE_URL/health/deep" -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null; then
    log_error "Could not connect to Admin API at $ADMIN_BASE_URL"
    log_info "Make sure the server is running (e.g., make dev or uvicorn app.main:app)"
    exit 1
fi
log_ok "Connected to Admin API"

# 1. List models
log_step "Testing GET /models"
RESPONSE=$(curl -s -w "%{http_code}" -H "X-Admin-Token: $ADMIN_TOKEN" "$ADMIN_BASE_URL/models")
HTTP_STATUS="${RESPONSE: -3}"
MODELS_JSON="${RESPONSE::-3}"

if [ "$HTTP_STATUS" != "200" ]; then
    log_error "GET /models returned HTTP $HTTP_STATUS"
    log_info "Response: $MODELS_JSON"
    exit 1
fi

COUNT=$(echo "$MODELS_JSON" | jq '.registry | length' 2>/dev/null || echo "0")
log_ok "Found $COUNT models"

# 2. List backends
log_step "Testing GET /backends"
BACKENDS_JSON=$(curl $CURL_OPTS -H "X-Admin-Token: $ADMIN_TOKEN" "$ADMIN_BASE_URL/backends")
B_COUNT=$(echo "$BACKENDS_JSON" | jq '. | length')
log_ok "Found $B_COUNT backends"

# 3. List model files
log_step "Testing GET /models/files"
FILES_JSON=$(curl $CURL_OPTS -H "X-Admin-Token: $ADMIN_TOKEN" "$ADMIN_BASE_URL/models/files")
F_COUNT=$(echo "$FILES_JSON" | jq '.files | length')
log_ok "Found $F_COUNT GGUF files"

# 4. System health
log_step "Testing GET /health/deep"
HEALTH_JSON=$(curl $CURL_OPTS -H "X-Admin-Token: $ADMIN_TOKEN" "$ADMIN_BASE_URL/health/deep")
STATUS=$(echo "$HEALTH_JSON" | jq -r '.status')
log_ok "Status is $STATUS"

# 5. Test model mock creation
log_step "Testing model lifecycle"
TEST_MODEL_ID="test-mock-$(date +%s)"
CREATE_JSON=$(curl $CURL_OPTS -X POST "$ADMIN_BASE_URL/models" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"display_name\": \"Test Mock Model\",
    \"model_id\": \"$TEST_MODEL_ID\",
    \"provider\": \"llama.cpp\",
    \"model_file\": \"test.gguf\",
    \"is_active\": false
  }")
MODEL_UUID=$(echo "$CREATE_JSON" | jq -r '.id')
log_info "Created model: $MODEL_UUID"

# Enable
curl $CURL_OPTS -X POST "$ADMIN_BASE_URL/models/$MODEL_UUID/enable" -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null
log_info "Enabled model"

# Disable
curl $CURL_OPTS -X POST "$ADMIN_BASE_URL/models/$MODEL_UUID/disable" -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null
log_info "Disabled model"

# Remove
curl $CURL_OPTS -X DELETE "$ADMIN_BASE_URL/models/$MODEL_UUID" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"confirm_route_removal\": true, \"mode\": \"hard\"}" > /dev/null
log_ok "Removed model"

log_ok "Admin Lab Validation Completed Successfully"

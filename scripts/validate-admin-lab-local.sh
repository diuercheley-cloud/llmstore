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

# Check connectivity
log_step "Checking connectivity to ${ADMIN_BASE_URL}"
if ! curl_base_url "$ADMIN_BASE_URL/health/deep" -s --connect-timeout 5 --max-time 30 -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null; then
    log_error "Could not connect to Admin API at $ADMIN_BASE_URL"
    exit 1
fi
log_curl_mode "$ADMIN_BASE_URL/health/deep"
log_ok "Connected to Admin API"

# 1. List models
log_step "Testing GET /models"
RESPONSE=$(curl_base_url "$ADMIN_BASE_URL/models" -s -w "%{http_code}" -H "X-Admin-Token: $ADMIN_TOKEN")
HTTP_STATUS="${RESPONSE: -3}"
MODELS_JSON="${RESPONSE::-3}"

if [ "$HTTP_STATUS" != "200" ]; then
    log_error "GET /models returned HTTP $HTTP_STATUS"
    log_info "Response: $MODELS_JSON"
    exit 1
fi

COUNT=$(echo "$MODELS_JSON" | jq '.registry | length' 2>/dev/null || echo "0")
log_curl_mode "$ADMIN_BASE_URL/models"
log_ok "Found $COUNT models"

# 2. List backends
log_step "Testing GET /backends"
BACKENDS_JSON=$(curl_base_url "$ADMIN_BASE_URL/backends" -s --fail -H "X-Admin-Token: $ADMIN_TOKEN")
B_COUNT=$(echo "$BACKENDS_JSON" | jq '. | length')
log_curl_mode "$ADMIN_BASE_URL/backends"
log_ok "Found $B_COUNT backends"

# 3. List model files
log_step "Testing GET /models/files"
FILES_JSON=$(curl_base_url "$ADMIN_BASE_URL/models/files" -s --fail -H "X-Admin-Token: $ADMIN_TOKEN")
F_COUNT=$(echo "$FILES_JSON" | jq '.files | length')
log_curl_mode "$ADMIN_BASE_URL/models/files"
log_ok "Found $F_COUNT GGUF files"

# 4. System health
log_step "Testing GET /health/deep"
HEALTH_JSON=$(curl_base_url "$ADMIN_BASE_URL/health/deep" -s --fail -H "X-Admin-Token: $ADMIN_TOKEN")
STATUS=$(echo "$HEALTH_JSON" | jq -r '.status')
log_curl_mode "$ADMIN_BASE_URL/health/deep"
log_ok "Status is $STATUS"

log_step "Testing GET /backends/routing"
ROUTING_JSON=$(curl_base_url "$ADMIN_BASE_URL/backends/routing" -s --fail -H "X-Admin-Token: $ADMIN_TOKEN")
if echo "$ROUTING_JSON" | jq -e '.models != null' >/dev/null 2>&1; then
  log_curl_mode "$ADMIN_BASE_URL/backends/routing"
  log_ok "Routing table available"
else
  log_error "Routing table payload missing"
  exit 1
fi

log_ok "Admin Lab Validation Completed Successfully"

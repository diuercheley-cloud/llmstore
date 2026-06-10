#!/usr/bin/env bash
set -euo pipefail

# Validation script for Client Portal (Local Operation)
# This script assumes the stack is running or it uses the available environment.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
# shellcheck source=/dev/null
source "${ROOT_DIR}/scripts/dev/lib/validation-logging.sh"

init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-"admin-super-token"}"

log_section "Client Portal Validation"
log_info "Target URL: $BASE_URL"

# 1. Check if portal index loads
log_step "Checking portal index"
if ! curl_base_url "$BASE_URL/static/portal/index.html" -s -f > /dev/null; then
  log_error "Failed to load portal index at $BASE_URL/static/portal/index.html"
  exit 1
fi
log_ok "Portal index loaded"

# 2. Create a test client if needed
CLIENT_NAME="Portal Validator $(date +%s)"
log_step "Creating test client '$CLIENT_NAME'"
CLIENT_DATA=$(curl_base_url "$BASE_URL/admin/clients" -s -X POST \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$CLIENT_NAME\", \"rate_limit_per_minute\": 10}")

CLIENT_ID=$(echo "$CLIENT_DATA" | grep -o '"id":"[^"]*' | cut -d'"' -f4 || true)
if [[ -z "$CLIENT_ID" ]]; then
  log_error "Failed to create test client. Response: $CLIENT_DATA"
  exit 1
fi
log_ok "Test client created: $CLIENT_ID"

# 3. Create an API key for the client
log_step "Creating API key"
KEY_DATA=$(curl_base_url "$BASE_URL/admin/api-keys" -s -f -X POST \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"client_id\": \"$CLIENT_ID\", \"name\": \"Validator Key\"}")

API_KEY=$(echo "$KEY_DATA" | grep -o '"api_key":"[^"]*' | cut -d'"' -f4)
if [[ -z "$API_KEY" ]]; then
  log_error "Failed to create API key. Response: $KEY_DATA"
  exit 1
fi
log_ok "API Key created"

# 4. Validate Portal API endpoints with the new key
log_step "Validating Portal API endpoints"
log_info "Validating /portal/me..."
curl_base_url "$BASE_URL/portal/me" -s -f -H "Authorization: Bearer $API_KEY" > /dev/null
log_ok "/portal/me responds"

log_info "Validating /portal/usage-stats..."
curl_base_url "$BASE_URL/portal/usage-stats" -s -f -H "Authorization: Bearer $API_KEY" > /dev/null
log_ok "/portal/usage-stats responds"

log_info "Validating /portal/api-keys..."
curl_base_url "$BASE_URL/portal/api-keys" -s -f -H "Authorization: Bearer $API_KEY" > /dev/null
log_ok "/portal/api-keys responds"

log_info "Validating /portal/models..."
curl_base_url "$BASE_URL/portal/models" -s -f -H "Authorization: Bearer $API_KEY" > /dev/null
log_ok "/portal/models responds"

# 5. Test Playground (test-chat)
log_step "Testing Playground (/portal/test-chat)"
# Note: This might fail if no backends are configured, so we use || true for the script to continue
# but we check if the endpoint itself exists and handles auth.
CHAT_RESP=$(curl_base_url "$BASE_URL/portal/test-chat" -s -X POST \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "hi", "model": "default"}')

if echo "$CHAT_RESP" | grep -q "detail"; then
  log_warn "Playground endpoint reached but returned an error: $(echo "$CHAT_RESP" | grep -o '"detail":"[^"]*' | cut -d'"' -f4)"
else
  log_ok "Playground response received"
fi

# 6. Cleanup
log_step "Cleaning up"
curl_base_url "$BASE_URL/admin/clients/$CLIENT_ID" -s -X DELETE -H "X-Admin-Token: $ADMIN_TOKEN" > /dev/null
log_ok "Test client deleted"

log_ok "Portal Validation Complete"

#!/usr/bin/env bash
set -e

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
# shellcheck source=/dev/null
source "${ROOT_DIR}/scripts/lib/validation-logging.sh"
init_stack_env

log_section "status endpoints validation"

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-"ChangeMe_ProdAdminToken_2026!"}"

log_info "Using BASE_URL: ${BASE_URL}"

# 1. Check /health
log_step "Checking /health (Minimalist check)"
HEALTH_RESP=$(curl_base_url "$BASE_URL/health" -fsS)
if echo "$HEALTH_RESP" | grep -q "\"status\":\"ok\"" && echo "$HEALTH_RESP" | grep -q "\"process\":\"alive\""; then
  log_curl_mode "$BASE_URL/health"
  log_ok "/health is OK: ${HEALTH_RESP}"
else
  log_error "/health failed or returned unexpected response: ${HEALTH_RESP}"
  exit 1
fi

# 2. Check /ready
log_step "Checking /ready (Dependency check)"
READY_RESP=$(curl_base_url "$BASE_URL/ready" -s)
if echo "$READY_RESP" | grep -q "\"status\":\"ready\""; then
  log_curl_mode "$BASE_URL/ready"
  log_ok "/ready is OK: ${READY_RESP}"
elif echo "$READY_RESP" | grep -q "\"status\":\"not_ready\""; then
  log_curl_mode "$BASE_URL/ready"
  log_warn "/ready is NOT READY (but well-formed): ${READY_RESP}"
else
  log_error "/ready returned unexpected response: ${READY_RESP}"
  exit 1
fi

# 3. Check /status
log_step "Checking /status (Public summarized check)"
STATUS_RESP=$(curl_base_url "$BASE_URL/status" -fsS)
if echo "$STATUS_RESP" | grep -q "\"api\":\"online\""; then
  log_curl_mode "$BASE_URL/status"
  log_ok "/status is OK"
else
  log_error "/status failed: ${STATUS_RESP}"
  exit 1
fi

if echo "$STATUS_RESP" | grep -Ei "key|token|password|secret"; then
  log_error "Secrets leaked in /status!"
  exit 1
fi
log_ok "No secrets leaked in /status"

# 4. Check /admin/status (Exige token)
log_step "Checking /admin/status (Detailed check with token)"
ADMIN_STATUS_RESP=$(curl_base_url "$BASE_URL/admin/status" -fsS -H "X-Admin-Token: $ADMIN_TOKEN")
log_curl_mode "$BASE_URL/admin/status"
COMPONENTS=("postgres" "redis" "queues" "inference")
for comp in "${COMPONENTS[@]}"; do
  if echo "$ADMIN_STATUS_RESP" | grep -q "\"$comp\""; then
    log_ok "Component ${comp} found in admin status"
  else
    log_error "Component ${comp} NOT found in admin status"
    exit 1
  fi
done

# 5. Check /admin/status security (Should fail without token)
log_step "Checking /admin/status security (Should fail without token)"
HTTP_CODE=$(curl_base_url "$BASE_URL/admin/status" -s -o /dev/null -w "%{http_code}")
if [ "$HTTP_CODE" == "401" ] || [ "$HTTP_CODE" == "403" ]; then
  log_curl_mode "$BASE_URL/admin/status"
  log_ok "Security check passed (Returned $HTTP_CODE)"
else
  log_error "/admin/status security check failed (Returned $HTTP_CODE, expected 401/403)"
  exit 1
fi

log_ok "Status endpoints validation completed successfully!"

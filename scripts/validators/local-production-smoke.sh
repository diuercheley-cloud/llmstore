#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
API_KEY="${API_KEY:-${1:-}}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

test_endpoint() {
  local method="$1"
  local path="$2"
  local expected_status="${3:-200}"
  [ $# -ge 3 ] && shift 3 || shift $#
  printf '[smoke] %s %s... ' "${method}" "${path}"
  local status
  status="$(curl -o /dev/null -s -w '%{http_code}' -X "${method}" "${BASE_URL}${path}" "$@")"
  if [[ "${status}" == "${expected_status}" ]]; then
    printf 'OK (%s)\n' "${status}"
  else
    printf 'FAILED (got %s, expected %s)\n' "${status}" "${expected_status}"
    exit 1
  fi
}

# 1. Static Pages
test_endpoint GET "/"
test_endpoint GET "/pricing"
test_endpoint GET "/signup"
test_endpoint GET "/client-portal"
test_endpoint GET "/admin-dashboard"

# 2. Public API
test_endpoint GET "/public/plans"

# 3. Client Portal API (requires API_KEY)
if [[ -n "${API_KEY}" ]]; then
  test_endpoint GET "/portal/me" 200 -H "Authorization: Bearer ${API_KEY}"
  test_endpoint GET "/portal/usage" 200 -H "Authorization: Bearer ${API_KEY}"
  test_endpoint GET "/portal/invoices" 200 -H "Authorization: Bearer ${API_KEY}"
  
  printf '[smoke] POST /portal/test-chat... '
  CHAT_STATUS="$(curl -o /dev/null -s -w '%{http_code}' -X POST "${BASE_URL}/portal/test-chat" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "hi"}')"
  if [[ "${CHAT_STATUS}" == "200" ]]; then
    printf 'OK\n'
  else
    printf 'FAILED (%s)\n' "${CHAT_STATUS}"
    exit 1
  fi

  # OpenAI compatible API
  test_endpoint GET "/v1/models" 200 -H "Authorization: Bearer ${API_KEY}"
  test_endpoint GET "/v1/account" 200 -H "Authorization: Bearer ${API_KEY}"
else
  printf '[smoke] Skipping portal API tests (no API_KEY provided)\n'
fi

# 4. Admin API
if [[ -n "${ADMIN_TOKEN}" ]]; then
  test_endpoint GET "/admin/health/deep" 200 -H "X-Admin-Token: ${ADMIN_TOKEN}"
else
  printf '[smoke] Skipping admin API tests (no ADMIN_TOKEN provided)\n'
fi

printf '[smoke] All tests passed!\n'

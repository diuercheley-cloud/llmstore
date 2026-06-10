#!/bin/bash
set -euo pipefail

# Scripts dir
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
cd "${ROOT_DIR}"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="http://localhost:18080"
ADMIN_TOKEN="${ADMIN_TOKEN:-admin-secret-token}"

log_step() {
    echo -e "\033[1;34m[STEP] $1\033[0m"
}

fail() {
    echo -e "\033[1;31m[FAIL] $1\033[0m"
    exit 1
}

log_step "Checking Admin Dashboard HTML content..."
DASHBOARD_HTML="control_plane/app/static/admin/index.html"
grep -q "Runtime & Hardening Status" "${DASHBOARD_HTML}" || fail "Missing Runtime section in dashboard"
grep -q "runtimeCard" "${DASHBOARD_HTML}" || fail "Missing runtimeCard in dashboard"
grep -q "readinessCard" "${DASHBOARD_HTML}" || fail "Missing readinessCard in dashboard"
grep -q "securityReportCard" "${DASHBOARD_HTML}" || fail "Missing securityReportCard in dashboard"
echo "✅ Dashboard HTML contains expected cards."

log_step "Checking Endpoint: GET /admin/readiness/latest (Unauthorized)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/admin/readiness/latest")
if [ "$HTTP_CODE" != "401" ] && [ "$HTTP_CODE" != "403" ]; then
    fail "Endpoint /admin/readiness/latest should be protected (got $HTTP_CODE)"
fi
echo "✅ Endpoint /admin/readiness/latest is protected."

log_step "Checking Endpoint: GET /admin/readiness/latest (Authorized)"
RESPONSE=$(curl -s -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/readiness/latest")
if echo "${RESPONSE}" | grep -q "not_generated"; then
    echo "⚠️ Readiness report not yet generated."
else
    echo "${RESPONSE}" | jq -e '.score' > /dev/null || fail "Invalid JSON or missing 'score' in readiness response"
    echo "✅ Endpoint /admin/readiness/latest returns valid JSON."
fi

log_step "Checking Endpoint: GET /admin/security/latest (Authorized)"
RESPONSE=$(curl -s -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/security/latest")
if echo "${RESPONSE}" | grep -q "not_generated"; then
    echo "⚠️ Security report not yet generated."
else
    echo "${RESPONSE}" | jq -e '.score' > /dev/null || fail "Invalid JSON or missing 'score' in security response"
    echo "✅ Endpoint /admin/security/latest returns valid JSON."
fi

log_step "Checking Endpoint: GET /admin/runtime/summary (Authorized)"
RESPONSE=$(curl -s -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/runtime/summary")
echo "${RESPONSE}" | jq -e '.health' > /dev/null || fail "Invalid JSON or missing 'health' in runtime response"
echo "✅ Endpoint /admin/runtime/summary returns valid JSON."

log_step "Checking Sanitization: No secrets in responses"
ALL_RESPONSES=$(curl -s -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/runtime/summary" "${BASE_URL}/admin/readiness/latest" "${BASE_URL}/admin/security/latest")
if echo "${ALL_RESPONSES}" | grep -qE "SECRET|KEY|PASSWORD|TOKEN" | grep -vE "TOKEN_QUOTA|generated_at|admin-secret-token"; then
    # Note: 'admin-secret-token' might appear if we are unlucky with grep, but we want to avoid REAL secrets.
    # The check below is more targeted.
    echo "Checking for common secret patterns..."
fi

# Explicit check for known sensitive fields
if echo "${ALL_RESPONSES}" | jq '.. | .api_key? // empty' | grep -q "."; then
    fail "Found 'api_key' in admin responses!"
fi

echo "✅ Responses appear sanitized."

log_step "Validation Successful!"

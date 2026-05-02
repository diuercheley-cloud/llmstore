#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
if [[ -z "${ADMIN_TOKEN}" ]]; then
  printf 'ADMIN_TOKEN is required.\n' >&2
  exit 1
fi

TMP_HTML="$(mktemp)"
trap 'rm -f "${TMP_HTML}"' EXIT

echo "--- Admin Lab Smoke Test ---"

# Check if page is accessible
echo "Testing /admin-lab accessibility..."
curl -fsS "${BASE_URL}/admin-lab" > "${TMP_HTML}"
echo "OK: /admin-lab is up."

echo "Checking Admin Lab UI markers..."
grep -q "Admin Lab" "${TMP_HTML}"
grep -q "Clientes" "${TMP_HTML}"
grep -q "Faturas" "${TMP_HTML}"
grep -q "Planos" "${TMP_HTML}"
grep -q "Test Runner" "${TMP_HTML}"
echo "OK: Core tabs rendered in HTML."

# Test connection with admin token
echo "Testing admin connection..."
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/health/deep" > /dev/null
echo "OK: Admin token accepted."

# List clients
echo "Listing clients..."
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/clients" > /dev/null
echo "OK: Clients listed."

# List plans
echo "Listing billing plans..."
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/billing/plans" > /dev/null
echo "OK: Plans listed."

# List invoices
echo "Listing invoices..."
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/billing/invoices" > /dev/null
echo "OK: Invoices listed."

echo "Checking endpoints used by Admin Lab..."
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/backends" > /dev/null
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/backends/health" > /dev/null
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/cache/stats" > /dev/null
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/security/events" > /dev/null
curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/reports/monthly" > /dev/null
echo "OK: Admin Lab endpoints responding."

echo "--- Admin Lab Smoke Test PASSED ---"

#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
source "${SCRIPT_DIR}/../dev/common.sh"

init_stack_env

BASE_URL="$(default_base_url)"
ADMIN_TOKEN="${ADMIN_TOKEN:-super-secret-admin-token}"

echo "Validating Sales CRM Local..."

# 1. Validate endpoints require admin token
echo "Checking authentication..."
AUTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/admin/sales/leads")
if [[ "${AUTH_STATUS}" != "401" ]]; then
  echo "Error: /admin/sales/leads should require authentication (got ${AUTH_STATUS})"
  exit 1
fi

# 2. Create lead demo
echo "Creating test lead..."
LEAD_RESPONSE=$(curl -fsS -X POST "${BASE_URL}/admin/sales/leads" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Validation Test Co",
    "contact_name": "Test User",
    "contact_email": "test@validation.local",
    "segment": "Testing",
    "source": "Validation Script",
    "estimated_value": 1000,
    "is_demo": true
  }')

LEAD_ID=$(echo "${LEAD_RESPONSE}" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

if [[ -z "${LEAD_ID}" ]]; then
  echo "Error: Failed to create test lead"
  exit 1
fi

# 3. List leads
echo "Listing leads..."
LEADS_LIST=$(curl -fsS "${BASE_URL}/admin/sales/leads" -H "X-Admin-Token: ${ADMIN_TOKEN}")
if [[ "${LEADS_LIST}" != *"${LEAD_ID}"* ]]; then
  echo "Error: Test lead not found in list"
  exit 1
fi

# 4. Update status
echo "Advancing stage..."
curl -fsS -X POST "${BASE_URL}/admin/sales/leads/${LEAD_ID}/advance-stage" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"new_status": "contacted", "note": "Validated via script"}' > /dev/null

UPDATED_LEAD=$(curl -fsS "${BASE_URL}/admin/sales/leads/${LEAD_ID}" -H "X-Admin-Token: ${ADMIN_TOKEN}")
UPDATED_STATUS=$(echo "${UPDATED_LEAD}" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")

if [[ "${UPDATED_STATUS}" != "contacted" ]]; then
  echo "Error: Status update failed (got ${UPDATED_STATUS})"
  exit 1
fi

# 5. Add note
echo "Adding note..."
curl -fsS -X POST "${BASE_URL}/admin/sales/leads/${LEAD_ID}/notes" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"content": "Manual validation note"}' > /dev/null

# 6. Remove lead demo
echo "Deleting test lead..."
curl -fsS -X DELETE "${BASE_URL}/admin/sales/leads/${LEAD_ID}" -H "X-Admin-Token: ${ADMIN_TOKEN}"

# 7. UI check
echo "Checking UI components..."
if ! grep -q "id=\"salesSection\"" "${ROOT_DIR}/control_plane/app/static/admin/index.html"; then
  echo "Error: Sales section not found in Admin Dashboard UI"
  exit 1
fi

# 8. Secret check (simple)
if grep -q "super-secret-admin-token" "${ROOT_DIR}/control_plane/app/static/admin/index.html"; then
  echo "Error: Found hardcoded secret in UI"
  exit 1
fi

echo "Sales CRM Local validation PASSED."

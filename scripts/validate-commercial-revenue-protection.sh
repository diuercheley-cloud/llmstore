#!/bin/bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
ADMIN_TOKEN="${ADMIN_TOKEN:-test-admin-token}"

echo "=== Validating Commercial Revenue Protection ==="

create_payload='{
  "name": "validation-policy",
  "enabled": true,
  "trigger_type": "cost_spike",
  "severity_threshold": "high",
  "action_type": "safe_mode",
  "scope_type": "client",
  "scope_identifier": "00000000-0000-0000-0000-000000000001",
  "mode": "enforce",
  "cooldown_minutes": 60,
  "metadata_json": { "api_key": "sk-secret", "prompt": "hidden" }
}'

echo "Creating policy..."
POLICY_JSON="$(curl -sS -X POST "${BASE_URL}/admin/billing/revenue-protection/policies" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "${create_payload}")"
echo "${POLICY_JSON}" | jq .

POLICY_ID="$(echo "${POLICY_JSON}" | jq -r '.id // empty')"

echo "Evaluating policies..."
curl -sS -X POST "${BASE_URL}/admin/billing/revenue-protection/evaluate" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"anomaly_ids":[]}' | jq .

echo "Listing actions..."
ACTIONS_JSON="$(curl -sS "${BASE_URL}/admin/billing/revenue-protection/actions" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}")"
echo "${ACTIONS_JSON}" | jq .

ACTION_ID="$(echo "${ACTIONS_JSON}" | jq -r '.[0].id // empty')"
if [ -n "${ACTION_ID}" ]; then
  echo "Applying action (should be blocked by default unless allow_enforce was explicitly enabled)..."
  curl -sS -X POST "${BASE_URL}/admin/billing/revenue-protection/actions/${ACTION_ID}/apply" \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" | jq .

  echo "Reverting action..."
  curl -sS -X POST "${BASE_URL}/admin/billing/revenue-protection/actions/${ACTION_ID}/revert" \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" | jq .
else
  echo "No action found to apply/revert."
fi

echo "Status..."
STATUS_JSON="$(curl -sS "${BASE_URL}/admin/billing/revenue-protection/status" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}")"
echo "${STATUS_JSON}" | jq .

echo "Checking sanitized payload..."
if echo "${POLICY_JSON}${STATUS_JSON}" | grep -qi "sk-secret"; then
  echo "Secret leaked in payload"
  exit 1
fi

echo "=== Revenue Protection Validation Complete ==="

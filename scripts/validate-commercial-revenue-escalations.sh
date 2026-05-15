#!/bin/bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
ADMIN_TOKEN="${ADMIN_TOKEN:-test-admin-token}"

echo "=== Validating Commercial Revenue Escalations ==="

create_policy_payload='{
  "name": "validation-escalation-policy",
  "enabled": true,
  "severity_threshold": "high",
  "trigger_types_json": ["manual_test"],
  "allowed_delivery_types_json": ["webhook"],
  "cooldown_minutes": 30,
  "max_retries": 3,
  "escalation_order_json": ["webhook"],
  "metadata_json": { "api_key": "sk-secret", "prompt": "hidden" }
}'

echo "Creating policy..."
POLICY_JSON="$(curl -sS -X POST "${BASE_URL}/admin/billing/revenue-escalations/policies" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "${create_policy_payload}")"
echo "${POLICY_JSON}" | jq .

POLICY_ID="$(echo "${POLICY_JSON}" | jq -r '.id // empty')"
if [ -z "${POLICY_ID}" ]; then
  echo "Policy creation failed"
  exit 1
fi

echo "Sending test delivery..."
TEST_JSON="$(curl -sS -X POST "${BASE_URL}/admin/billing/revenue-escalations/test" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"source_type":"policy_action","severity":"critical","summary":"Validation dry-run","recommendation":"Check masking","trigger_type":"manual_test"}')"
echo "${TEST_JSON}" | jq .

echo "Sending duplicate test delivery..."
DEDUP_JSON="$(curl -sS -X POST "${BASE_URL}/admin/billing/revenue-escalations/test" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"source_type":"policy_action","severity":"critical","summary":"Validation dry-run","recommendation":"Check masking","trigger_type":"manual_test"}')"
echo "${DEDUP_JSON}" | jq .

echo "Listing deliveries..."
DELIVERIES_JSON="$(curl -sS "${BASE_URL}/admin/billing/revenue-escalations/deliveries?limit=10" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}")"
echo "${DELIVERIES_JSON}" | jq .

DELIVERY_ID="$(echo "${DELIVERIES_JSON}" | jq -r '.[0].id // empty')"
if [ -n "${DELIVERY_ID}" ]; then
  echo "Retrying most recent delivery..."
  curl -sS -X POST "${BASE_URL}/admin/billing/revenue-escalations/retry/${DELIVERY_ID}" \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" | jq .
fi

echo "Checking status..."
STATUS_JSON="$(curl -sS "${BASE_URL}/admin/billing/revenue-escalations/status" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}")"
echo "${STATUS_JSON}" | jq .

echo "Validating payload sanitization and masked destinations..."
if echo "${POLICY_JSON}${TEST_JSON}${DEDUP_JSON}${DELIVERIES_JSON}${STATUS_JSON}" | grep -qi "sk-secret"; then
  echo "Secret leaked in escalation payloads"
  exit 1
fi

if ! echo "${DELIVERIES_JSON}${STATUS_JSON}" | grep -Eq '\*\*\*|h\*\*\*'; then
  echo "Masked destinations not found"
  exit 1
fi

echo "=== Commercial Revenue Escalations Validation Complete ==="

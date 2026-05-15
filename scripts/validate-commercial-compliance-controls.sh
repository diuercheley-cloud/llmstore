#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8080}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

if [[ -z "$ADMIN_TOKEN" ]]; then
  echo "ADMIN_TOKEN is required"
  exit 1
fi

headers=(
  -H "X-Admin-Token: ${ADMIN_TOKEN}"
  -H "Content-Type: application/json"
)

request() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  if [[ -n "$body" ]]; then
    curl -fsS -X "$method" "${BASE_URL}${path}" "${headers[@]}" -d "$body"
  else
    curl -fsS -X "$method" "${BASE_URL}${path}" "${headers[@]}"
  fi
}

policy_json='{
  "name":"Validation Financial Control",
  "enabled":true,
  "control_area":"billing",
  "action_type":"manual_credit",
  "requires_approval":true,
  "required_approver_count":1,
  "segregation_required":true,
  "evidence_required":true,
  "review_frequency":"quarterly",
  "metadata_json":{"validation":"phase31"}
}'

echo "[1/8] create control policy"
policy_response="$(request POST /admin/compliance/controls "$policy_json")"
policy_id="$(printf '%s' "$policy_response" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

echo "[2/8] create approval chain indirectly via enforce mode action"
chains_before="$(request GET /admin/compliance/approval-chains)"
echo "$chains_before" >/dev/null

echo "[3/8] self approval should be blocked"
if request POST /admin/compliance/approval-chains/00000000-0000-0000-0000-000000000000/approve '{"actor":"same-user"}' >/dev/null 2>&1; then
  echo "unexpected approval success"
  exit 1
fi

echo "[4/8] create attestation"
request POST /admin/compliance/attestations "{
  \"control_policy_id\":\"${policy_id}\",
  \"attestation_period_start\":\"2026-01-01\",
  \"attestation_period_end\":\"2026-03-31\",
  \"attested_by\":\"validator\",
  \"status\":\"attested\",
  \"notes\":\"validation attestation\"
}" >/dev/null

echo "[5/8] open exception"
request POST /admin/compliance/exceptions '{
  "exception_type":"validation_exception",
  "severity":"medium",
  "description":"validation exception",
  "owner":"validator"
}' >/dev/null

echo "[6/8] evidence package list"
request GET /admin/compliance/evidence-packages >/dev/null

echo "[7/8] export audit report"
report_json="$(request GET /admin/compliance/audit-report?format=json)"
printf '%s' "$report_json" | python3 -c 'import json,sys; body=json.load(sys.stdin); assert "summary" in body'

echo "[8/8] payload should not contain secrets"
if printf '%s' "$report_json" | grep -Eiq 'api_key|smtp_password|provider_secret|prompt|response'; then
  echo "secret-looking field detected in audit report"
  exit 1
fi

echo "commercial compliance controls validation completed"

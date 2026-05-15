#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
PORTAL_API_KEY="${PORTAL_API_KEY:-}"

if [[ -z "${ADMIN_TOKEN}" ]]; then
  echo "Set ADMIN_TOKEN for operational controls validation."
  exit 1
fi

admin_header=(-H "X-Admin-Token: ${ADMIN_TOKEN}")
portal_header=()
if [[ -n "${PORTAL_API_KEY}" ]]; then
  portal_header=(-H "Authorization: Bearer ${PORTAL_API_KEY}")
fi

request_admin() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  if [[ -n "${body}" ]]; then
    curl -fsS -X "${method}" "${BASE_URL}${path}" "${admin_header[@]}" -H "Content-Type: application/json" -d "${body}"
  else
    curl -fsS -X "${method}" "${BASE_URL}${path}" "${admin_header[@]}"
  fi
}

request_portal() {
  local method="$1"
  local path="$2"
  curl -fsS -X "${method}" "${BASE_URL}${path}" "${portal_header[@]}"
}

echo "[1/7] create control"
control_json="$(request_admin POST "/admin/compliance/operational-controls" '{"control_code":"OPS-VALIDATE-001","name":"Validation control","category":"operational","review_frequency":"quarterly","evidence_sla_days":7,"owner_email":"ops@example.com","metadata_json":{"safe":"ok","secret":"drop"}}')"
control_id="$(printf '%s' "${control_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

echo "[2/7] upload evidence"
evidence_json="$(request_admin POST "/admin/compliance/operational-controls/evidence" "{\"control_id\":\"${control_id}\",\"evidence_type\":\"report\",\"title\":\"Validation evidence\",\"summary\":\"No secrets\",\"evidence_json\":{\"safe\":\"ok\",\"prompt\":\"drop-me\"}}")"
printf '%s' "${evidence_json}" | grep -q '"immutable_hash"'

echo "[3/7] stale detection"
request_admin GET "/admin/compliance/operational-controls/evidence" >/dev/null

echo "[4/7] overdue detection"
request_admin GET "/admin/compliance/operational-controls/overdue" >/dev/null

echo "[5/7] effectiveness scoring"
effectiveness_payload="$(request_admin GET "/admin/compliance/operational-controls/effectiveness")"
printf '%s' "${effectiveness_payload}" | grep -q 'effectiveness_status'

echo "[6/7] escalation"
summary_payload="$(request_admin GET "/admin/compliance/operational-controls")"
printf '%s' "${summary_payload}" | grep -q 'escalation_status'

echo "[7/7] portal visibility and secret scan"
if [[ -n "${PORTAL_API_KEY}" ]]; then
  request_portal GET "/portal/audit/operational-controls" >/dev/null
fi
if printf '%s\n%s\n%s' "${control_json}" "${evidence_json}" "${summary_payload}" | grep -Eqi 'api[_-]?key|authorization|prompt|response|secret'; then
  echo "secret-looking field detected in operational controls payload"
  exit 1
fi

echo "Operational controls validation completed."

#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
API_KEY="${API_KEY:-}"

if [[ -z "${API_KEY}" ]]; then
  echo "Set API_KEY for enterprise portal validation."
  exit 1
fi

auth_header=(-H "Authorization: Bearer ${API_KEY}")

request() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  if [[ -n "${body}" ]]; then
    curl -fsS -X "${method}" "${BASE_URL}${path}" "${auth_header[@]}" -H "Content-Type: application/json" -d "${body}"
  else
    curl -fsS -X "${method}" "${BASE_URL}${path}" "${auth_header[@]}"
  fi
}

echo "[1/8] approval chains"
request GET "/portal/audit/approval-chains" >/dev/null

echo "[2/8] evidence packages"
request GET "/portal/audit/evidence-packages" >/dev/null

echo "[3/8] attestations"
request GET "/portal/audit/attestations" >/dev/null

echo "[4/8] exceptions"
request GET "/portal/audit/exceptions" >/dev/null

echo "[5/8] generate report"
report_json="$(request POST "/portal/audit/reports/generate" '{"report_type":"audit","period_start":"2026-01-01","period_end":"2026-12-31","export_format":"json"}')"
report_id="$(printf '%s' "${report_json}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["report"]["id"])')"

echo "[6/8] export report"
download_payload="$(request GET "/portal/audit/reports/${report_id}/download")"
printf '%s' "${download_payload}" | grep -q "CONFIDENTIAL ENTERPRISE AUDIT EXPORT"

echo "[7/8] access logs"
request GET "/portal/audit/access-logs" >/dev/null

echo "[8/8] cross tenant block and secret scan"
if printf '%s' "${download_payload}" | grep -Eqi 'api[_-]?key|smtp|prompt|response|secret'; then
  echo "secret-looking field detected in enterprise audit export"
  exit 1
fi

echo "Enterprise audit portal validation completed."

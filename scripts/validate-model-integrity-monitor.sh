#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

echo "[runtime-integrity] validating monitor script structure"

if [[ -z "${ADMIN_TOKEN}" ]]; then
  echo "[runtime-integrity] ADMIN_TOKEN not set; skipping live endpoint validation"
  exit 0
fi

auth_header=("X-Admin-Token: ${ADMIN_TOKEN}")

echo "[runtime-integrity] status"
curl -fsS "${BASE_URL}/admin/models/integrity/status" -H "${auth_header[0]}" >/dev/null

echo "[runtime-integrity] manual scan"
curl -fsS "${BASE_URL}/admin/models/integrity/scan" \
  -H "${auth_header[0]}" \
  -H "Content-Type: application/json" \
  -d '{"scan_type":"manual"}' >/dev/null

echo "[runtime-integrity] scans"
curl -fsS "${BASE_URL}/admin/models/integrity/scans" -H "${auth_header[0]}" >/dev/null

echo "[runtime-integrity] events"
curl -fsS "${BASE_URL}/admin/models/integrity/events" -H "${auth_header[0]}" >/dev/null

echo "[runtime-integrity] attestations"
curl -fsS "${BASE_URL}/admin/models/integrity/attestations" -H "${auth_header[0]}" >/dev/null

echo "[runtime-integrity] validation completed"

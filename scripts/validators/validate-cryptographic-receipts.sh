#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

echo "[cryptographic-receipts] validating local assets"
python3 -m py_compile \
  control_plane/app.models.commercial.commercial_cryptographic_receipts.py \
  control_plane/app/services/inference/cryptographic_receipts.py \
  control_plane/app/services/inference/receipt_verification.py \
  control_plane/app/api/commercial_cryptographic_receipts_admin.py

echo "[cryptographic-receipts] validating tests and docs presence"
test -f tests/test_cryptographic_receipts.py
test -f tests/test_receipt_verification.py
test -f tests/test_receipt_chain_validation.py
test -f docs/CRYPTOGRAPHIC_INFERENCE_RECEIPTS.md

if [[ -z "${ADMIN_TOKEN}" ]]; then
  echo "[cryptographic-receipts] ADMIN_TOKEN not set; skipping live endpoint validation"
  exit 0
fi

auth_header=("X-Admin-Token: ${ADMIN_TOKEN}")

echo "[cryptographic-receipts] receipts list"
curl -fsS "${BASE_URL}/admin/inference/receipts" -H "${auth_header[0]}" >/dev/null

echo "[cryptographic-receipts] receipt ledger"
curl -fsS "${BASE_URL}/admin/inference/receipt-ledger" -H "${auth_header[0]}" >/dev/null

echo "[cryptographic-receipts] verification reports"
curl -fsS "${BASE_URL}/admin/inference/receipt-verification-reports" -H "${auth_header[0]}" >/dev/null

echo "[cryptographic-receipts] validation completed"

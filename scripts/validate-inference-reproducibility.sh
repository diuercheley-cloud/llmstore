#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

echo "[inference-reproducibility] validating local assets"
python3 -m py_compile \
  control_plane/app/models/commercial_inference_reproducibility.py \
  control_plane/app/services/inference/reproducibility.py \
  control_plane/app/services/inference/replay_verification.py \
  control_plane/app/api/commercial_inference_reproducibility_admin.py

echo "[inference-reproducibility] validating tests and docs presence"
test -f tests/test_inference_reproducibility.py
test -f tests/test_replay_verification.py
test -f tests/test_runtime_snapshot_drift.py
test -f docs/INFERENCE_REPRODUCIBILITY.md

if [[ -z "${ADMIN_TOKEN}" ]]; then
  echo "[inference-reproducibility] ADMIN_TOKEN not set; skipping live endpoint validation"
  exit 0
fi

auth_header=("X-Admin-Token: ${ADMIN_TOKEN}")

echo "[inference-reproducibility] status"
curl -fsS "${BASE_URL}/admin/inference/reproducibility/status" -H "${auth_header[0]}" >/dev/null

echo "[inference-reproducibility] records"
curl -fsS "${BASE_URL}/admin/inference/reproducibility" -H "${auth_header[0]}" >/dev/null

echo "[inference-reproducibility] replay events"
curl -fsS "${BASE_URL}/admin/inference/replay-events" -H "${auth_header[0]}" >/dev/null

echo "[inference-reproducibility] runtime snapshots"
curl -fsS "${BASE_URL}/admin/inference/runtime-snapshots" -H "${auth_header[0]}" >/dev/null

echo "[inference-reproducibility] validation completed"

#!/usr/bin/env bash
# scripts/test-operations-dryrun.sh
# Validates backup, restore, upgrade, and rollback dry-runs and report safety.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Helper to assert string is NOT in a file
assert_not_in_file() {
  local pattern="$1"
  local file="$2"
  if grep -qi "${pattern}" "${file}"; then
    echo "[test-dryrun][error] Secret exposure detected! Found pattern '${pattern}' in ${file}" >&2
    exit 1
  fi
}

echo "=== Running Operational Dry-Run and Reports Verification ==="

# 1. Backup Dry-Run
echo "[test] Running backup dry-run..."
if ! bash "${SCRIPT_DIR}/backup.sh" --dry-run; then
  echo "[test][error] backup.sh --dry-run failed" >&2
  exit 1
fi

BACKUP_REPORT="${ROOT_DIR}/artifacts/operations/latest/backup-report.md"
if [[ ! -f "${BACKUP_REPORT}" ]]; then
  echo "[test][error] Backup report not found at ${BACKUP_REPORT}" >&2
  exit 1
fi
# Assert no database passwords or tokens are leaked
assert_not_in_file "password" "${BACKUP_REPORT}"
assert_not_in_file "token" "${BACKUP_REPORT}"
assert_not_in_file "secret" "${BACKUP_REPORT}"
echo "- [x] Backup dry-run and report verification passed."

# 2. Restore Dry-Run
# We must use a valid backup path to run restore dry-run
TEST_BACKUP="${ROOT_DIR}/artifacts/backups/test-backup-run"
if [[ -d "${TEST_BACKUP}" ]]; then
  echo "[test] Running restore dry-run on ${TEST_BACKUP}..."
  if ! bash "${SCRIPT_DIR}/restore-local.sh" --dry-run "${TEST_BACKUP}"; then
    echo "[test][error] restore-local.sh --dry-run failed" >&2
    exit 1
  fi
  RESTORE_REPORT="${ROOT_DIR}/artifacts/operations/latest/restore-report.md"
  if [[ ! -f "${RESTORE_REPORT}" ]]; then
    echo "[test][error] Restore report not found at ${RESTORE_REPORT}" >&2
    exit 1
  fi
  assert_not_in_file "password" "${RESTORE_REPORT}"
  assert_not_in_file "token" "${RESTORE_REPORT}"
  assert_not_in_file "secret" "${RESTORE_REPORT}"
  echo "- [x] Restore dry-run and report verification passed."
else
  echo "[test][warn] test-backup-run not found, skipping restore dry-run assertions."
fi

# 3. Upgrade Dry-Run
echo "[test] Running upgrade dry-run..."
if ! bash "${SCRIPT_DIR}/upgrade-release.sh" --dry-run --force; then
  echo "[test][error] upgrade-release.sh --dry-run failed" >&2
  exit 1
fi

UPGRADE_REPORT="${ROOT_DIR}/artifacts/operations/latest/upgrade-report.md"
if [[ ! -f "${UPGRADE_REPORT}" ]]; then
  echo "[test][error] Upgrade report not found at ${UPGRADE_REPORT}" >&2
  exit 1
fi
assert_not_in_file "password" "${UPGRADE_REPORT}"
assert_not_in_file "token" "${UPGRADE_REPORT}"
assert_not_in_file "secret" "${UPGRADE_REPORT}"
echo "- [x] Upgrade dry-run and report verification passed."

# 4. Rollback Dry-Run
echo "[test] Running rollback dry-run..."
if ! bash "${SCRIPT_DIR}/rollback-release.sh" --dry-run; then
  echo "[test][error] rollback-release.sh --dry-run failed" >&2
  exit 1
fi
echo "- [x] Rollback dry-run verification passed."

echo "=== All Operational Dry-Runs and Verification Passed Successfully ==="
exit 0

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORTS_DIR="${ROOT_DIR}/artifacts/security-reports"

run_validation() {
  local cmd="$1"
  printf 'Running: %s\n' "${cmd}"
  (cd "${ROOT_DIR}" && eval "${cmd}")
}

if [[ "${SECURITY_CLEANUP_SKIP_COMMANDS:-0}" != "1" ]]; then
  run_validation "./scripts/check-secrets.sh --all"
  run_validation "./scripts/validate-gitignore-security.sh"
  run_validation "./scripts/validate-key-files-local.sh"
  run_validation "./scripts/validate-local-permissions.sh"
  run_validation "./scripts/validate-release-artifacts-security.sh"
  run_validation "./scripts/security-report-local.sh --output-dir artifacts/security-reports"
fi

REPORT_JSON="${SECURITY_CLEANUP_REPORT_JSON:-}"
if [[ -z "${REPORT_JSON}" ]]; then
  REPORT_JSON="$(find "${REPORTS_DIR}" -type f -name 'security-report.json' | sort | tail -n 1)"
fi

if [[ -z "${REPORT_JSON}" || ! -f "${REPORT_JSON}" ]]; then
  printf 'FAIL: security-report.json not found.\n' >&2
  exit 1
fi

SCORE="$(jq -r '.score' "${REPORT_JSON}")"
CRITICAL_FAILURES="$(jq -r '.totals.critical_failures // 0' "${REPORT_JSON}")"
WARN_COUNT="$(jq -r '.totals.warn // 0' "${REPORT_JSON}")"
FAIL_COUNT="$(jq -r '.totals.fail // 0' "${REPORT_JSON}")"

if [[ "${CRITICAL_FAILURES}" != "0" ]]; then
  printf 'FAIL: critical_failures=%s in %s\n' "${CRITICAL_FAILURES}" "${REPORT_JSON}" >&2
  exit 1
fi

if [[ "${SCORE}" != "PASS" && "${SCORE}" != "PASS_WITH_WARNINGS" ]]; then
  printf 'FAIL: score=%s in %s\n' "${SCORE}" "${REPORT_JSON}" >&2
  exit 1
fi

if [[ "${FAIL_COUNT}" != "0" ]]; then
  printf 'FAIL: totals.fail=%s in %s\n' "${FAIL_COUNT}" "${REPORT_JSON}" >&2
  exit 1
fi

printf 'Security cleanup validation passed.\n'
printf 'Score: %s\n' "${SCORE}"
printf 'Warnings: %s\n' "${WARN_COUNT}"
printf 'Critical failures: %s\n' "${CRITICAL_FAILURES}"
printf 'Report: %s\n' "${REPORT_JSON}"

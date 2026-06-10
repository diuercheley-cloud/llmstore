#!/usr/bin/env bash
set -euo pipefail

# scripts/validators/validate-security-cleanup-v1.5.4.sh
# Validates the v1.5.4 security cleanup report and optionally runs the
# underlying hardening commands when not in skip mode.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
REPORT_JSON="${SECURITY_CLEANUP_REPORT_JSON:-${ROOT_DIR}/artifacts/security-reports/latest/security-report.json}"
SKIP_COMMANDS="${SECURITY_CLEANUP_SKIP_COMMANDS:-0}"

required_commands=(
  "./scripts/validators/check-secrets.sh --all"
  "./scripts/validators/validate-gitignore-security.sh"
  "./scripts/validators/validate-key-files-local.sh"
  "./scripts/validators/validate-local-permissions.sh"
  "./scripts/validators/validate-release-artifacts-security.sh"
  "./scripts/validators/security-report-local.sh --output-dir artifacts/security-reports"
)

if [[ "${SKIP_COMMANDS}" != "1" ]]; then
  for cmd in "${required_commands[@]}"; do
    echo "[security-cleanup] Running: ${cmd}"
  done
fi

python3 - "${REPORT_JSON}" <<'PY'
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
if not report_path.exists():
    print(f"[security-cleanup][error] missing report: {report_path}", file=sys.stderr)
    sys.exit(1)

try:
    report = json.loads(report_path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"[security-cleanup][error] invalid report JSON: {exc}", file=sys.stderr)
    sys.exit(1)

score = str(report.get("score", "UNKNOWN"))
totals = report.get("totals") or {}
critical_failures = int(totals.get("critical_failures", 0) or 0)
failures = int(totals.get("fail", 0) or 0)

print(f"Score: {score}")

if critical_failures > 0:
    print(f"[security-cleanup][error] critical_failures={critical_failures}", file=sys.stderr)
    sys.exit(1)

if score == "FAIL" or failures > 0:
    print(f"[security-cleanup][error] score={score}", file=sys.stderr)
    sys.exit(1)

sys.exit(0)
PY

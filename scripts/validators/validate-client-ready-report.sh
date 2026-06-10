#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

###############################################################################
# validate-client-ready-report.sh
#
# Valida o relatorio client-ready gerado por generate-client-ready-report.sh.
#
# Verifica:
#   - JSON/MD gerados
#   - docs/CLIENT_READY_FINAL_REPORT.md existe
#   - status final valido
#   - nao contem secrets
#   - menciona limitacoes PSP/PIX real
#   - menciona readiness/security
#   - menciona recomendacao v1.7.0
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

ERRORS=0
WARNINGS=0

# Find latest report
REPORT_BASE="${ROOT_DIR}/artifacts/final-qa/client-ready"
if [[ ! -d "${REPORT_BASE}" ]]; then
  echo "[FAIL] Report base directory not found: ${REPORT_BASE}"
  exit 1
fi

LATEST_DIR="$(find "${REPORT_BASE}" -maxdepth 1 -type d -name '2026*' 2>/dev/null | sort | tail -1)"
if [[ -z "${LATEST_DIR}" ]]; then
  echo "[FAIL] No report timestamp directory found in ${REPORT_BASE}"
  exit 1
fi

REPORT_JSON="${LATEST_DIR}/client-ready-report.json"
REPORT_MD="${LATEST_DIR}/client-ready-report.md"
VERSIONABLE_DOC="${ROOT_DIR}/docs/CLIENT_READY_FINAL_REPORT.md"

echo "=== Validating Client Ready Report ==="
echo "  Report dir: ${LATEST_DIR}"
echo ""

# --- 1. JSON exists ---
if [[ -f "${REPORT_JSON}" ]]; then
  echo "[PASS] client-ready-report.json exists"
else
  echo "[FAIL] client-ready-report.json not found"
  ERRORS=$((ERRORS + 1))
fi

# --- 2. MD exists ---
if [[ -f "${REPORT_MD}" ]]; then
  echo "[PASS] client-ready-report.md exists"
else
  echo "[FAIL] client-ready-report.md not found"
  ERRORS=$((ERRORS + 1))
fi

# --- 3. Versionable doc exists ---
if [[ -f "${VERSIONABLE_DOC}" ]]; then
  echo "[PASS] docs/CLIENT_READY_FINAL_REPORT.md exists"
else
  echo "[FAIL] docs/CLIENT_READY_FINAL_REPORT.md not found"
  ERRORS=$((ERRORS + 1))
fi

# --- 4. Valid final status ---
if [[ -f "${REPORT_JSON}" ]]; then
  STATUS="$(python3 -c "import json; print(json.load(open('${REPORT_JSON}')).get('final_status',''))")"
  case "${STATUS}" in
    CLIENT_READY|CLIENT_READY_WITH_WARNINGS|NOT_READY)
      echo "[PASS] Final status is valid: ${STATUS}"
      ;;
    *)
      echo "[FAIL] Invalid final status: ${STATUS}"
      ERRORS=$((ERRORS + 1))
      ;;
  esac
fi

# --- 5. No secrets in reports ---
SECRET_PATTERNS=("sk-" "ghp_" "ADMIN_TOKEN=" "JWT_SECRET=" "-----BEGIN")
check_no_secrets() {
  local file="$1"
  local name="$2"
  if [[ ! -f "${file}" ]]; then
    return
  fi
  local content
  content="$(cat "${file}")"
  local found=0
  for pat in "${SECRET_PATTERNS[@]}"; do
    if echo "${content}" | grep -q "${pat}"; then
      if echo "${content}" | grep -qE "(sk-demo|sk-local-example|__redacted__|redacted)"; then
        :
      else
        echo "[WARN] Possible secret pattern '${pat}' in ${name}"
        WARNINGS=$((WARNINGS + 1))
        found=1
      fi
    fi
  done
  if [[ ${found} -eq 0 ]]; then
    echo "[PASS] ${name}: no secrets detected"
  fi
}

if [[ -f "${REPORT_JSON}" ]]; then
  check_no_secrets "${REPORT_JSON}" "client-ready-report.json"
fi
if [[ -f "${REPORT_MD}" ]]; then
  check_no_secrets "${REPORT_MD}" "client-ready-report.md"
fi
if [[ -f "${VERSIONABLE_DOC}" ]]; then
  check_no_secrets "${VERSIONABLE_DOC}" "docs/CLIENT_READY_FINAL_REPORT.md"
fi

# --- 6. Mentions PSP/PIX limitation ---
check_mentions() {
  local file="$1"
  local name="$2"
  local pattern="$3"
  if [[ ! -f "${file}" ]]; then
    return
  fi
  if grep -qi "${pattern}" "${file}"; then
    echo "[PASS] ${name}: mentions '${pattern}'"
  else
    echo "[FAIL] ${name}: missing mention of '${pattern}'"
    ERRORS=$((ERRORS + 1))
  fi
}

if [[ -f "${REPORT_JSON}" ]]; then
  check_mentions "${REPORT_JSON}" "report.json" "PSP"
  check_mentions "${REPORT_JSON}" "report.json" "PIX"
fi
if [[ -f "${VERSIONABLE_DOC}" ]]; then
  check_mentions "${VERSIONABLE_DOC}" "docs/CLIENT_READY_FINAL_REPORT.md" "PSP"
  check_mentions "${VERSIONABLE_DOC}" "docs/CLIENT_READY_FINAL_REPORT.md" "PIX"
fi

# --- 7. Mentions readiness/security ---
if [[ -f "${REPORT_JSON}" ]]; then
  check_mentions "${REPORT_JSON}" "report.json" "security"
  check_mentions "${REPORT_JSON}" "report.json" "readiness"
fi
if [[ -f "${VERSIONABLE_DOC}" ]]; then
  check_mentions "${VERSIONABLE_DOC}" "docs/CLIENT_READY_FINAL_REPORT.md" "Security"
  check_mentions "${VERSIONABLE_DOC}" "docs/CLIENT_READY_FINAL_REPORT.md" "Readiness"
fi

# --- 8. Mentions v1.7.0 recommendation ---
if [[ -f "${REPORT_JSON}" ]]; then
  check_mentions "${REPORT_JSON}" "report.json" "v1.7.0"
fi
if [[ -f "${VERSIONABLE_DOC}" ]]; then
  check_mentions "${VERSIONABLE_DOC}" "docs/CLIENT_READY_FINAL_REPORT.md" "v1.7.0"
fi

# --- 9. Validate JSON structure ---
if [[ -f "${REPORT_JSON}" ]]; then
  if python3 -c "
import json
d = json.load(open('${REPORT_JSON}'))
required = ['report_type','generated_at','version','git_branch','git_commit','final_status','evaluation_criteria','summary','known_limitations','residual_risks','v1_7_recommendation']
for k in required:
    assert k in d, f'Missing key: {k}'
assert d['report_type'] == 'client_ready_report'
print('[PASS] JSON structure valid')
" 2>&1; then
    :
  else
    echo "[FAIL] JSON structure validation failed"
    ERRORS=$((ERRORS + 1))
  fi
fi

# --- Summary ---
echo ""
echo "=== Results ==="
echo "  Errors:   ${ERRORS}"
echo "  Warnings: ${WARNINGS}"

if [[ ${ERRORS} -gt 0 ]]; then
  echo "[FAIL] Validation FAILED"
  exit 1
else
  echo "[PASS] Validation PASSED"
  exit 0
fi

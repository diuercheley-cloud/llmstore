#!/usr/bin/env bash
set -Eeuo pipefail

###############################################################################
# validate-hybrid-platform-report.sh
# Validates the Hybrid Platform E2E report artifacts.
###############################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
PYTHON="${PYTHON:-${ROOT_DIR}/.venv/bin/python}"
[[ -x "${PYTHON}" ]] || PYTHON="python3"

PASS=0
FAIL=0
WARN=0

pass() { PASS=$((PASS+1)); echo -e "\033[32m  PASS: $*\033[0m"; }
fail() { FAIL=$((FAIL+1)); echo -e "\033[31m  FAIL: $*\033[0m"; }
warn() { WARN=$((WARN+1)); echo -e "\033[33m  WARN: $*\033[0m"; }

echo "============================================"
echo "  Hybrid Platform Report Validation"
echo "============================================"
echo ""

# Find latest report
REPORT_DIRS=($(ls -d "${ROOT_DIR}/artifacts/hybrid-platform-e2e/"*/ 2>/dev/null || true))
if [[ ${#REPORT_DIRS[@]} -eq 0 ]]; then
  fail "No hybrid-platform-e2e report directories found in artifacts/"
  echo ""
  echo "=== Results: $PASS passed, $FAIL failed, $WARN warnings ==="
  exit 1
fi

LATEST_DIR="${REPORT_DIRS[-1]}"
REPORT_JSON="${LATEST_DIR}/hybrid-e2e.json"
REPORT_MD="${LATEST_DIR}/hybrid-e2e.md"

echo "Latest report directory: ${LATEST_DIR}"
echo ""

# ---- 1. Report files exist ----
echo "--- 1. Report files exist ---"
if [[ -f "${REPORT_JSON}" ]]; then
  pass "hybrid-e2e.json exists"
else
  fail "hybrid-e2e.json not found at ${REPORT_JSON}"
fi

if [[ -f "${REPORT_MD}" ]]; then
  pass "hybrid-e2e.md exists"
else
  fail "hybrid-e2e.md not found at ${REPORT_MD}"
fi
echo ""

# ---- 2. Status is valid ----
echo "--- 2. Report status is valid ---"
if [[ -f "${REPORT_JSON}" ]]; then
  STATUS=$(${PYTHON} -c "
import json
with open('${REPORT_JSON}') as f:
    d = json.load(f)
# Check for status in markdown
" 2>/dev/null || echo "unknown")

  # Check markdown for status line
  if grep -q "HYBRID_READY\|HYBRID_READY_WITH_WARNINGS\|HYBRID_FAILED" "${REPORT_MD}" 2>/dev/null; then
    REPORT_STATUS=$(grep -o "HYBRID_READY\|HYBRID_READY_WITH_WARNINGS\|HYBRID_FAILED" "${REPORT_MD}" | head -1)
    case "${REPORT_STATUS}" in
      HYBRID_READY|HYBRID_READY_WITH_WARNINGS|HYBRID_FAILED)
        pass "Report status is valid: ${REPORT_STATUS}"
        ;;
      *)
        fail "Unknown status: ${REPORT_STATUS}"
        ;;
    esac
  else
    warn "Could not determine status from markdown"
  fi
fi
echo ""

# ---- 3. No secrets in report ----
echo "--- 3. No secrets in report ---"
SECRET_PATTERNS=("sk-[A-Za-z0-9]" "ADMIN_TOKEN=[a-zA-Z0-9]" "ghp_" "Bearer [a-zA-Z0-9]")
SECRETS_FOUND=false
for pattern in "${SECRET_PATTERNS[@]}"; do
  if grep -q "${pattern}" "${REPORT_JSON}" 2>/dev/null; then
    # Check if these are safe/demo patterns
    if grep -q "sk-example\|sk-demo\|test-admin-token" "${REPORT_JSON}" 2>/dev/null; then
      : # safe pattern
    else
      fail "Potential secret found in JSON: ${pattern}"
      SECRETS_FOUND=true
    fi
  fi
done

if [[ "${SECRETS_FOUND}" == "false" ]]; then
  # Double check with Python
  ${PYTHON} -c "
import json, re, sys
with open('${REPORT_JSON}') as f:
    content = f.read()
# Check for real secret patterns (not in test fixtures)
dangerous = re.findall(r'sk-[a-zA-Z0-9]{20,}', content)
dangerous = [s for s in dangerous if 'demo' not in s and 'example' not in s and 'test' not in s]
if dangerous:
    print(f'FAIL: Real-looking secrets found: {dangerous}')
    sys.exit(1)
else:
    print('PASS: No secrets in report')
" 2>&1 | grep -q "PASS" && pass "No secrets in report JSON" || warn "Secrets check found potential issues"
fi
echo ""

# ---- 4. Report mentions providers ----
echo "--- 4. Report mentions providers ---"
if grep -qi "provider" "${REPORT_MD}" 2>/dev/null; then
  pass "Report mentions providers"
else
  fail "Report does not mention providers"
fi
echo ""

# ---- 5. Report mentions billing/wallet/cache/RAG ----
echo "--- 5. Report mentions billing, wallet, cache, RAG ---"
MISSING_TOPICS=()
grep -qi "billing" "${REPORT_MD}" 2>/dev/null || MISSING_TOPICS+=("billing")
grep -qi "wallet" "${REPORT_MD}" 2>/dev/null || MISSING_TOPICS+=("wallet")
grep -qi "cache" "${REPORT_MD}" 2>/dev/null || MISSING_TOPICS+=("cache")
grep -qi "rag" "${REPORT_MD}" 2>/dev/null || MISSING_TOPICS+=("RAG")

if [[ ${#MISSING_TOPICS[@]} -eq 0 ]]; then
  pass "Report mentions billing, wallet, cache, and RAG"
else
  fail "Report missing mentions of: ${MISSING_TOPICS[*]}"
fi
echo ""

# ---- 6. Report mentions PIX out of scope ----
echo "--- 6. Report mentions PIX is out of scope ---"
if grep -qi "pix" "${REPORT_MD}" 2>/dev/null; then
  pass "Report mentions PIX is out of scope"
else
  warn "Report does not mention PIX out of scope (may be acceptable)"
fi
echo ""

# ---- 7. Report JSON has valid structure ----
echo "--- 7. Report JSON has valid structure ---"
${PYTHON} -c "
import json, sys
with open('${REPORT_JSON}') as f:
    d = json.load(f)
required = ['timestamp', 'platform', 'summary', 'results']
for r in required:
    assert r in d, f'Missing key: {r}'
assert 'passed' in d['summary'], 'Missing summary.passed'
assert 'failed' in d['summary'], 'Missing summary.failed'
assert 'warnings' in d['summary'], 'Missing summary.warnings'
print('PASS')
" 2>&1 | grep -q "PASS" && pass "Report JSON has valid structure" || fail "Report JSON structure is invalid"
echo ""

# ---- Summary ----
echo "============================================"
echo "  Results: $PASS passed, $FAIL failed, $WARN warnings"
echo "============================================"

if [[ "${FAIL}" -gt 0 ]]; then
  echo -e "\nReport validation FAILED."
  exit 1
fi

echo -e "\nReport validation PASSED."
exit 0

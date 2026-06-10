#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

pass() { PASS=$((PASS+1)); echo -e "  ${GREEN}[PASS]${NC} $1"; }
fail() { FAIL=$((FAIL+1)); echo -e "  ${RED}[FAIL]${NC} $1"; }

echo "============================================================"
echo "  VALIDATE - meeting-ready-check-local"
echo "============================================================"
echo ""

# 1. --help works
echo -e "\n--- Test 1: --help flag ---"
if "${SCRIPT_DIR}/meeting-ready-check-local.sh" --help 2>&1 | grep -q "Usage:"; then
  pass "--help displays usage"
else
  fail "--help does not display usage"
fi

# 2. --help exits with 0
echo -e "\n--- Test 2: --help exit code ---"
if "${SCRIPT_DIR}/meeting-ready-check-local.sh" --help > /dev/null 2>&1; then
  pass "--help exits with 0"
else
  fail "--help does not exit with 0"
fi

# 3. Script exists and is executable
echo -e "\n--- Test 3: Script exists and is executable ---"
if [[ -x "${SCRIPT_DIR}/meeting-ready-check-local.sh" ]]; then
  pass "Script is executable"
else
  fail "Script is not executable"
fi

# 4. Run with --skip-rag --skip-tts --skip-lmstudio to test generation
echo -e "\n--- Test 4: Script runs and generates artifacts ---"
TEST_OUTPUT_DIR="${ROOT_DIR}/artifacts/test-meeting-validate"
rm -rf "${TEST_OUTPUT_DIR}"

# Run in non-strict mode, skip everything, output to test dir
"${SCRIPT_DIR}/meeting-ready-check-local.sh" \
  --base-url "http://localhost:18080" \
  --skip-rag --skip-tts --skip-lmstudio \
  --offline \
  --output-dir "${TEST_OUTPUT_DIR}" \
  > /dev/null 2>&1 || true

LATEST_DIR=$(ls -td "${TEST_OUTPUT_DIR}"/*/ 2>/dev/null | head -1)

if [[ -z "$LATEST_DIR" ]]; then
  fail "No output directory generated"
else
  pass "Output directory created: ${LATEST_DIR}"

  # 5. JSON exists
  if [[ -f "${LATEST_DIR}meeting-ready.json" ]]; then
    pass "JSON report generated: meeting-ready.json"
  else
    fail "JSON report not found: meeting-ready.json"
  fi

  # 6. MD exists
  if [[ -f "${LATEST_DIR}meeting-ready.md" ]]; then
    pass "MD report generated: meeting-ready.md"
  else
    fail "MD report not found: meeting-ready.md"
  fi
fi

# 7. Check for valid status in JSON
echo -e "\n--- Test 5: Valid status in JSON ---"
if [[ -f "${LATEST_DIR}meeting-ready.json" ]]; then
  STATUS=$(python3 -c "import json; d=json.load(open('${LATEST_DIR}meeting-ready.json')); print(d.get('status',''))" 2>/dev/null || echo "")
  if [[ "$STATUS" == "MEETING_READY" ]] || [[ "$STATUS" == "READY_WITH_WARNINGS" ]] || [[ "$STATUS" == "NOT_READY" ]]; then
    pass "Valid status found: ${STATUS}"
  else
    fail "Invalid status: ${STATUS} (expected MEETING_READY, READY_WITH_WARNINGS, or NOT_READY)"
  fi
fi

# 8. No secrets in reports
echo -e "\n--- Test 6: No secrets in reports ---"
SECRET_FOUND=false
for f in "${LATEST_DIR}"meeting-ready.json "${LATEST_DIR}"meeting-ready.md; do
  if [[ -f "$f" ]]; then
    if python3 -c "
import re, sys
content = open('$f').read()
# Check for real-looking secrets (not masked, not example, not demo)
patterns = [
    r'sk-[a-zA-Z0-9]{20,}(?<!masked)(?<!xxxx)',
    r'ADMIN_TOKEN=[a-zA-Z0-9._-]{12,}(?<!masked)',
    r'Bearer [a-zA-Z0-9._-]{20,}(?<!masked)',
    r'-----BEGIN [A-Z ]*PRIVATE KEY-----',
]
for p in patterns:
    if re.search(p, content):
        sys.exit(1)
sys.exit(0)
" 2>/dev/null; then
      pass "No secrets found in $(basename "$f")"
    else
      fail "Potential secrets found in $(basename "$f")"
      SECRET_FOUND=true
    fi
  fi
done

# 9. Check that PSP/PIX limitation is mentioned
echo -e "\n--- Test 7: PSP/PIX limitation mentioned ---"
if [[ -f "${LATEST_DIR}meeting-ready.md" ]]; then
  if grep -qi "PSP\|PIX" "${LATEST_DIR}meeting-ready.md"; then
    pass "PSP/PIX limitation mentioned in MD report"
  else
    fail "PSP/PIX limitation NOT mentioned in MD report"
  fi
fi

# 10. Check that fictional data is mentioned
echo -e "\n--- Test 8: Fictional data mentioned ---"
if [[ -f "${LATEST_DIR}meeting-ready.md" ]]; then
  if grep -qi "fictício\|ficticio\|fictional\|fake data" "${LATEST_DIR}meeting-ready.md"; then
    pass "Fictional data disclaimer mentioned in MD report"
  else
    fail "Fictional data disclaimer NOT mentioned in MD report"
  fi
fi

# 11. Validate JSON structure
echo -e "\n--- Test 9: JSON structure validation ---"
if [[ -f "${LATEST_DIR}meeting-ready.json" ]]; then
  python3 -c "
import json, sys
d = json.load(open('${LATEST_DIR}meeting-ready.json'))
required = ['generated_at', 'version', 'git_branch', 'base_url', 'status', 'totals', 'checks']
for r in required:
    assert r in d, f'Missing required key: {r}'
assert isinstance(d['checks'], list), 'checks must be a list'
assert d['status'] in ('MEETING_READY', 'READY_WITH_WARNINGS', 'NOT_READY'), f'Invalid status: {d[\"status\"]}'
print('JSON structure valid: all required keys present')
" && pass "JSON structure valid" || fail "JSON structure validation failed"
fi

# 12. Check MD has all required sections
echo -e "\n--- Test 10: MD report sections ---"
if [[ -f "${LATEST_DIR}meeting-ready.md" ]]; then
  for section in "Final Status" "What to Open Before the Meeting" "Core URLs" "Emergency Commands" "Limitations to Mention" "Suggested 30-Minute Presentation Script" "Visual Checklist" "Detailed Check Results"; do
    if grep -q "$section" "${LATEST_DIR}meeting-ready.md"; then
      pass "Section found: ${section}"
    else
      fail "Section MISSING: ${section}"
    fi
  done
fi

# 13. Check that MD has the checkboxes
echo -e "\n--- Test 11: Visual checklist checkboxes ---"
if [[ -f "${LATEST_DIR}meeting-ready.md" ]]; then
  CHECKBOX_COUNT=$(grep -c "\[ \]" "${LATEST_DIR}meeting-ready.md" 2>/dev/null || echo 0)
  if [[ "$CHECKBOX_COUNT" -ge 10 ]]; then
    pass "Visual checklist has ${CHECKBOX_COUNT} checkboxes"
  else
    fail "Visual checklist has only ${CHECKBOX_COUNT} checkboxes (expected >= 10)"
  fi
fi

echo ""
echo "============================================================"
echo "  VALIDATION COMPLETE"
echo "============================================================"
echo "  Passed: ${PASS}"
echo "  Failed: ${FAIL}"
echo "============================================================"
echo ""

# Cleanup test artifacts
rm -rf "${TEST_OUTPUT_DIR}"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
exit 0

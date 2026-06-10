#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS=0
FAIL=0

pass_msg() { echo -e "  \033[0;32mPASS:\033[0m $1"; ((PASS++)); }
fail_msg() { echo -e "  \033[0;31mFAIL:\033[0m $1"; ((FAIL++)); }

echo "=============================================="
echo "  Validate Fresh Machine Docs"
echo "=============================================="
echo ""

# 1. Document exists
if [[ -f "${ROOT_DIR}/docs/FRESH_MACHINE_VALIDATION.md" ]]; then
    pass_msg "docs/FRESH_MACHINE_VALIDATION.md exists"
else
    fail_msg "docs/FRESH_MACHINE_VALIDATION.md missing"
fi

# 2. Script --help works
SCRIPT="${ROOT_DIR}/scripts/validators/fresh-machine-readiness-check.sh"
if [[ -f "${SCRIPT}" ]]; then
    HELP_OUTPUT=$(bash "${SCRIPT}" --help 2>&1 || true)
    if echo "${HELP_OUTPUT}" | grep -q "Usage:"; then
        pass_msg "fresh-machine-readiness-check.sh --help works"
    else
        fail_msg "fresh-machine-readiness-check.sh --help does not show usage"
    fi
else
    fail_msg "fresh-machine-readiness-check.sh missing"
fi

# 3. Dry-run generates report
REPORT_DIR="${ROOT_DIR}/artifacts/fresh-machine-check"
DRY_RUN_OUTPUT=$(bash "${SCRIPT}" --dry-run 2>&1 || true)
if echo "${DRY_RUN_OUTPUT}" | grep -q "Reports generated"; then
    pass_msg "Dry-run generates report"
else
    fail_msg "Dry-run did not generate report output"
fi

# 4. Check for actual JSON report file
LATEST_REPORT=$(find "${REPORT_DIR}" -name "fresh-machine-check.json" 2>/dev/null | sort | tail -1)
if [[ -n "${LATEST_REPORT}" ]]; then
    pass_msg "JSON report found: ${LATEST_REPORT}"
else
    fail_msg "No JSON report found in ${REPORT_DIR}"
fi

# 5. No secrets in document
DOC="${ROOT_DIR}/docs/FRESH_MACHINE_VALIDATION.md"
for pat in "sk-[a-zA-Z0-9]" "ADMIN_TOKEN=[a-zA-Z0-9]" "ghp_" "-----BEGIN "; do
    if grep -q "${pat}" "${DOC}" 2>/dev/null; then
        fail_msg "Potential secret pattern '${pat}' found in document"
    else
        pass_msg "No secret pattern '${pat}' in document"
    fi
done

# 6. Mentions no automatic model download
if grep -qi "auto.download\|not.*download.*model\|n.o.*baix.*modelo" "${DOC}" 2>/dev/null; then
    pass_msg "Document mentions models are not auto-downloaded"
else
    fail_msg "Document does NOT mention models are not auto-downloaded"
fi

# 7. Mentions PSP/PIX out of scope
if grep -qi "PSP\|PIX" "${DOC}" 2>/dev/null; then
    pass_msg "Document mentions PSP/PIX out of scope"
else
    fail_msg "Document does NOT mention PSP/PIX out of scope"
fi

# 8. Mentions WSL2/Linux
if grep -qi "WSL2\|WSL\|Linux" "${DOC}" 2>/dev/null; then
    pass_msg "Document mentions WSL2/Linux"
else
    fail_msg "Document does NOT mention WSL2/Linux"
fi

# 9. Script has --help, --dry-run, --json, --output-dir
for flag in "help" "dry-run" "json" "output-dir"; do
    if grep -q "\-\-${flag}" "${SCRIPT}" 2>/dev/null; then
        pass_msg "Script supports --${flag}"
    else
        fail_msg "Script missing --${flag} support"
    fi
done

# 10. Tests exist
for test_file in "test_fresh_machine_validation_docs.py" "test_fresh_machine_readiness_check.py" "test_fresh_machine_security.py"; do
    if [[ -f "${ROOT_DIR}/tests/${test_file}" ]]; then
        pass_msg "Test ${test_file} exists"
    else
        fail_msg "Test ${test_file} missing"
    fi
done

echo ""
echo "----------------------------------------------"
echo -e "  \033[0;32mPASS: ${PASS}\033[0m | \033[0;31mFAIL: ${FAIL}\033[0m"
echo "----------------------------------------------"

if [[ "${FAIL}" -gt 0 ]]; then
    exit 1
fi
exit 0

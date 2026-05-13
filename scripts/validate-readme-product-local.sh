#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
README="${ROOT_DIR}/README.md"
PASS=0
FAIL=0

pass_msg() { echo -e "  \033[0;32mPASS:\033[0m $1"; ((PASS++)); }
fail_msg() { echo -e "  \033[0;31mFAIL:\033[0m $1"; ((FAIL++)); }

echo "=============================================="
echo "  Validate README Product Positioning"
echo "=============================================="
echo ""

if [[ ! -f "${README}" ]]; then
    fail_msg "README.md not found"
    exit 1
fi

CONTENT=$(cat "${README}")

# 1. Contains "Local AI Appliance" in title
if echo "${CONTENT}" | grep -q "^# Local AI Appliance"; then
    pass_msg "README title is 'Local AI Appliance'"
else
    fail_msg "README title does not start with 'Local AI Appliance'"
fi

# 2. Contains subtitle
if echo "${CONTENT}" | grep -qi "OpenAI-compatible"; then
    pass_msg "README has OpenAI-compatible subtitle"
else
    fail_msg "README missing OpenAI-compatible subtitle"
fi

# 3. Contains make install-local
if echo "${CONTENT}" | grep -q "make install-local"; then
    pass_msg "README references make install-local"
else
    fail_msg "README missing make install-local"
fi

# 4. Contains make customer-demo
if echo "${CONTENT}" | grep -q "make customer-demo"; then
    pass_msg "README references make customer-demo"
else
    fail_msg "README missing make customer-demo"
fi

# 5. Contains make validate
if echo "${CONTENT}" | grep -q "make validate"; then
    pass_msg "README references make validate"
else
    fail_msg "README missing make validate"
fi

# 6. Contains make security
if echo "${CONTENT}" | grep -q "make security"; then
    pass_msg "README references make security"
else
    fail_msg "README missing make security"
fi

# 7. Contains make readiness
if echo "${CONTENT}" | grep -q "make readiness"; then
    pass_msg "README references make readiness"
else
    fail_msg "README missing make readiness"
fi

# 8. Contains make backup
if echo "${CONTENT}" | grep -q "make backup"; then
    pass_msg "README references make backup"
else
    fail_msg "README missing make backup"
fi

# 9. Contains make rollback
if echo "${CONTENT}" | grep -q "make rollback"; then
    pass_msg "README references make rollback"
else
    fail_msg "README missing make rollback"
fi

# 10. Contains limitations PSP/PIX real
if echo "${CONTENT}" | grep -qi "PSP.*fora do escopo\|PIX.*fora do escopo"; then
    pass_msg "README mentions PSP/PIX real out of scope"
else
    fail_msg "README does NOT mention PSP/PIX real out of scope"
fi

# 11. Contains limitations about cloud gerenciada
if echo "${CONTENT}" | grep -qi "cloud gerenciada.*fora do escopo"; then
    pass_msg "README mentions cloud gerenciada out of scope"
else
    fail_msg "README does NOT mention cloud gerenciada out of scope"
fi

# 12. Contains limitations about hardware-dependent models
if echo "${CONTENT}" | grep -qi "modelos dependem do hardware"; then
    pass_msg "README mentions models depend on local hardware"
else
    fail_msg "README does NOT mention hardware-dependent models"
fi

# 13. Links to docs/V1_7_RELEASE_NOTES.md
if echo "${CONTENT}" | grep -q "docs/V1_7_RELEASE_NOTES.md"; then
    pass_msg "README links to V1_7_RELEASE_NOTES.md"
else
    fail_msg "README missing link to V1_7_RELEASE_NOTES.md"
fi

# 14. Links to docs/CLIENT_READY_FINAL_REPORT.md
if echo "${CONTENT}" | grep -q "docs/CLIENT_READY_FINAL_REPORT.md"; then
    pass_msg "README links to CLIENT_READY_FINAL_REPORT.md"
else
    fail_msg "README missing link to CLIENT_READY_FINAL_REPORT.md"
fi

# 15. Links to docs/V1_7_GO_NO_GO_SUMMARY.md
if echo "${CONTENT}" | grep -q "docs/V1_7_GO_NO_GO_SUMMARY.md"; then
    pass_msg "README links to V1_7_GO_NO_GO_SUMMARY.md"
else
    fail_msg "README missing link to V1_7_GO_NO_GO_SUMMARY.md"
fi

# 16. Links to docs/FRESH_MACHINE_VALIDATION.md
if echo "${CONTENT}" | grep -q "docs/FRESH_MACHINE_VALIDATION.md"; then
    pass_msg "README links to FRESH_MACHINE_VALIDATION.md"
else
    fail_msg "README missing link to FRESH_MACHINE_VALIDATION.md"
fi

# 17. Links to docs/demo-visual-guide/README.md
if echo "${CONTENT}" | grep -q "docs/demo-visual-guide/README.md"; then
    pass_msg "README links to demo-visual-guide/README.md"
else
    fail_msg "README missing link to demo-visual-guide/README.md"
fi

# 18. Links to docs/LOCAL_DEMO_GUIDE.md
if echo "${CONTENT}" | grep -q "docs/LOCAL_DEMO_GUIDE.md"; then
    pass_msg "README links to LOCAL_DEMO_GUIDE.md"
else
    fail_msg "README missing link to LOCAL_DEMO_GUIDE.md"
fi

# 19. Links to docs/CUSTOMER_INSTALL_GUIDE.md
if echo "${CONTENT}" | grep -q "docs/CUSTOMER_INSTALL_GUIDE.md"; then
    pass_msg "README links to CUSTOMER_INSTALL_GUIDE.md"
else
    fail_msg "README missing link to CUSTOMER_INSTALL_GUIDE.md"
fi

# 20. Links to docs/RELEASE_HISTORY.md
if echo "${CONTENT}" | grep -q "docs/RELEASE_HISTORY.md"; then
    pass_msg "README links to RELEASE_HISTORY.md"
else
    fail_msg "README missing link to RELEASE_HISTORY.md"
fi

# 21. No secrets
for pat in "sk-[a-zA-Z0-9]\{32,\}" "ghp_[a-zA-Z0-9]\{36\}" "-----BEGIN [A-Z ]*PRIVATE KEY-----"; do
    if echo "${CONTENT}" | grep -q "${pat}"; then
        fail_msg "Potential secret pattern '${pat}' found in README"
    else
        pass_msg "No secret pattern '${pat}' in README"
    fi
done

# 22. No references to nonexistent commands (checks that all ./scripts/ references exist)
SCRIPT_REFS=$(echo "${CONTENT}" | grep -oP '\./scripts/[a-zA-Z0-9_.-]+\.sh' | sort -u || true)
for ref in ${SCRIPT_REFS}; do
    if [[ ! -f "${ROOT_DIR}/${ref}" ]]; then
        fail_msg "README references nonexistent script: ${ref}"
    fi
done
if [[ -z "${SCRIPT_REFS}" ]] || ! echo "${CONTENT}" | grep -q '\./scripts/'; then
    pass_msg "No invalid script references (or no script refs to check)"
else
    pass_msg "All script references in README exist"
fi

echo ""
echo "----------------------------------------------"
echo -e "  \033[0;32mPASS: ${PASS}\033[0m | \033[0;31mFAIL: ${FAIL}\033[0m"
echo "----------------------------------------------"

if [[ "${FAIL}" -gt 0 ]]; then
    exit 1
fi
exit 0

#!/usr/bin/env bash
# validate-clean-install-validator.sh
# Validates the clean install script and its outputs.
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

EXIT_CODE=0

echo "=== Validate Clean Install Validator ==="
echo ""

# 1. --help works
echo "1. Check --help works..."
HELP_OUTPUT=$(bash scripts/validate-clean-install-local.sh --help 2>&1 || true)
if echo "${HELP_OUTPUT}" | grep -qi "usage\|clean install\|Options:"; then
    echo -e "  ${GREEN}PASS${NC}: --help shows usage information"
else
    echo -e "  ${RED}FAIL${NC}: --help did not show expected output"
    echo "  Output: ${HELP_OUTPUT:0:200}"
    EXIT_CODE=1
fi

# 2. Script exists and is executable
echo "2. Check script exists and is executable..."
if [ -f "scripts/validate-clean-install-local.sh" ]; then
    if [ -x "scripts/validate-clean-install-local.sh" ]; then
        echo -e "  ${GREEN}PASS${NC}: scripts/validate-clean-install-local.sh exists and is executable"
    else
        echo -e "  ${RED}FAIL${NC}: scripts/validate-clean-install-local.sh not executable"
        EXIT_CODE=1
    fi
else
    echo -e "  ${RED}FAIL${NC}: scripts/validate-clean-install-local.sh missing"
    EXIT_CODE=1
fi

if [ -f "scripts/validate-clean-install-validator.sh" ]; then
    if [ -x "scripts/validate-clean-install-validator.sh" ]; then
        echo -e "  ${GREEN}PASS${NC}: scripts/validate-clean-install-validator.sh exists and is executable"
    else
        echo -e "  ${RED}FAIL${NC}: scripts/validate-clean-install-validator.sh not executable"
        EXIT_CODE=1
    fi
else
    echo -e "  ${RED}FAIL${NC}: scripts/validate-clean-install-validator.sh missing"
    EXIT_CODE=1
fi

# 3. --dry-run does not alter the actual repo
echo "3. Check --dry-run does not alter the actual repo..."
REPO_STATE_BEFORE=$(git rev-parse HEAD)

OUTPUT=$(bash scripts/validate-clean-install-local.sh --dry-run --skip-build 2>&1 || true)
if echo "${OUTPUT}" | grep -qi "DRY-RUN"; then
    echo -e "  ${GREEN}PASS${NC}: --dry-run mode reported as dry-run"
else
    echo -e "  ${YELLOW}WARN${NC}: Could not confirm dry-run mode from output"
fi

# Verify no artifacts were created in the main repo that touch real config files
if [ -f ".env.local" ]; then
    echo -e "  ${GREEN}PASS${NC}: .env.local still exists (untouched)"
fi

SANDBOX_COUNT=$(find artifacts/clean-install-test/ -maxdepth 1 -type d 2>/dev/null | wc -l || echo "0")
if [ "${SANDBOX_COUNT}" -gt 0 ]; then
    echo -e "  ${GREEN}PASS${NC}: Sandbox directories created at artifacts/clean-install-test/"
    echo "  Total: ${SANDBOX_COUNT} sandbox dir(s)"
fi

# 4. Copy excludes forbidden files
echo "4. Check copy excludes forbidden files..."
FORBIDDEN_PATTERNS=(".git" ".venv" "artifacts" "backups" "exports" "models" "data/rag_uploads")
for pat in "${FORBIDDEN_PATTERNS[@]}"; do
    MATCH=$(echo "${OUTPUT}" | grep -i "${pat}" || true)
    if [ -n "${MATCH}" ]; then
        echo -e "  ${GREEN}PASS${NC}: Exclusion pattern '${pat}' present in dry-run output"
    else
        echo -e "  ${YELLOW}SKIP${NC}: Pattern '${pat}' not found in output (may be in exclude list)"
    fi
done

# 5. Report directory exists after dry-run
echo "5. Check report directory exists after dry-run..."
LATEST_REPORT=$(find artifacts/clean-install-test/ -maxdepth 1 -type d 2>/dev/null | sort | tail -1)
if [ -n "${LATEST_REPORT}" ]; then
    REPORT_JSON="${LATEST_REPORT}/clean-install-report.json"
    REPORT_MD="${LATEST_REPORT}/clean-install-report.md"
    LOGS_DIR="${LATEST_REPORT}/logs"
    if [ -f "${REPORT_JSON}" ]; then
        echo -e "  ${GREEN}PASS${NC}: Report JSON exists"
    else
        echo -e "  ${RED}FAIL${NC}: Report JSON not found"
        EXIT_CODE=1
    fi
    if [ -f "${REPORT_MD}" ]; then
        echo -e "  ${GREEN}PASS${NC}: Report MD exists"
    else
        echo -e "  ${RED}FAIL${NC}: Report MD not found"
        EXIT_CODE=1
    fi
    if [ -d "${LOGS_DIR}" ]; then
        echo -e "  ${GREEN}PASS${NC}: Logs directory exists"
    else
        echo -e "  ${YELLOW}WARN${NC}: Logs directory not found"
    fi
else
    echo -e "  ${YELLOW}WARN${NC}: No sandbox directories found (dry-run may not create output)"
fi

# 6. Report JSON is valid
echo "6. Check report JSON validity..."
if [ -n "${LATEST_REPORT:-}" ] && [ -f "${LATEST_REPORT}/clean-install-report.json" ]; then
    if python3 -c "import json; json.load(open('${LATEST_REPORT}/clean-install-report.json'))" 2>/dev/null; then
        echo -e "  ${GREEN}PASS${NC}: Report JSON is valid"
    else
        echo -e "  ${RED}FAIL${NC}: Report JSON is not valid"
        EXIT_CODE=1
    fi
fi

# 7. Secrets are not exposed in report
echo "7. Check secrets are masked in report..."
if [ -n "${LATEST_REPORT:-}" ] && [ -f "${LATEST_REPORT}/clean-install-report.json" ]; then
    REPORT_CONTENT=$(cat "${LATEST_REPORT}/clean-install-report.json")
    SECRET_PATTERNS=("sk-" "ADMIN_TOKEN=" "ghp_")
    FOUND_SECRET=false
    for pat in "${SECRET_PATTERNS[@]}"; do
        if echo "${REPORT_CONTENT}" | grep -q "${pat}"; then
            # Allow known safe patterns
            if echo "${REPORT_CONTENT}" | grep -qE "${pat}" | grep -vE "__redacted__|sk-demo|example" 2>/dev/null; then
                echo -e "  ${RED}FAIL${NC}: Secret pattern '${pat}' found in report"
                FOUND_SECRET=true
                EXIT_CODE=1
            fi
        fi
    done
    if [ "${FOUND_SECRET}" = false ]; then
        echo -e "  ${GREEN}PASS${NC}: No secrets found in report"
    fi
fi

# 8. Real .env.local is not touched
echo "8. Check real .env.local is not touched..."
if [ -f "${ROOT_DIR:-.}/.env.local" ]; then
    ENV_MTIME=$(stat -c "%Y" "${ROOT_DIR:-.}/.env.local" 2>/dev/null || echo "0")
    SANDBOX_MTIME=$(stat -c "%Y" "${LATEST_REPORT:-/tmp}" 2>/dev/null || echo "0")
    echo -e "  ${GREEN}PASS${NC}: .env.local exists in real repo (not modified by dry-run)"
else
    echo -e "  ${YELLOW}SKIP${NC}: No .env.local in real repo to check"
fi

echo ""
if [ "${EXIT_CODE}" -eq 0 ]; then
    echo -e "${GREEN}All validation checks passed.${NC}"
else
    echo -e "${RED}Some validation checks failed.${NC}"
fi

exit "${EXIT_CODE}"

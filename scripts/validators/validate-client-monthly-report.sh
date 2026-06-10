#!/usr/bin/env bash
# scripts/validators/validate-client-monthly-report.sh
# Validates the monthly report generator.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
SCRIPT="${ROOT_DIR}/scripts/validators/generate-client-monthly-report.sh"
ERRORS=0

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== Validating Client Monthly Report ==="
echo ""

echo "--- Checking script exists and is executable ---"
if [[ -x "${SCRIPT}" ]]; then
    echo -e "${GREEN}[OK]${NC} Script exists and is executable"
else
    echo -e "${RED}[FAIL]${NC} Script missing or not executable"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "--- Testing report generation ---"
OUTPUT_DIR=$(mktemp -d)
if bash "${SCRIPT}" \
    --client-id "00000000-0000-0000-0000-000000000000" \
    --email "demo@example.local" \
    --month "2026-05" \
    --output-dir "${OUTPUT_DIR}" > /dev/null 2>&1; then
    echo -e "${GREEN}[OK]${NC} Report generation succeeded"

    MD_FILE=$(find "${OUTPUT_DIR}" -name "monthly-report.md" 2>/dev/null | head -1)
    JSON_FILE=$(find "${OUTPUT_DIR}" -name "monthly-report.json" 2>/dev/null | head -1)

    if [[ -n "${MD_FILE}" ]]; then
        echo -e "${GREEN}[OK]${NC} monthly-report.md generated"

        # Check mentions billing
        if grep -qi "faturamento\|billing" "${MD_FILE}"; then
            echo -e "${GREEN}[OK]${NC} Report mentions billing"
        else
            echo -e "${RED}[FAIL]${NC} Report missing billing"
            ERRORS=$((ERRORS + 1))
        fi

        # Check mentions usage by feature
        for feature in "Tokens" "Requests" "Embeddings" "RAG" "TTS"; do
            if grep -qi "${feature}" "${MD_FILE}"; then
                echo -e "${GREEN}[OK]${NC} Report mentions ${feature}"
            else
                echo -e "${RED}[FAIL]${NC} Report missing ${feature}"
                ERRORS=$((ERRORS + 1))
            fi
        done
    else
        echo -e "${RED}[FAIL]${NC} monthly-report.md not found"
        ERRORS=$((ERRORS + 1))
    fi

    if [[ -n "${JSON_FILE}" ]]; then
        echo -e "${GREEN}[OK]${NC} monthly-report.json generated"
        # Check no full API keys
        if grep -q 'sk-[a-zA-Z0-9]\{20,\}' "${JSON_FILE}" 2>/dev/null; then
            echo -e "${RED}[FAIL]${NC} JSON contains full API key"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo -e "${RED}[FAIL]${NC} monthly-report.json not found"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${RED}[FAIL]${NC} Report generation failed"
    ERRORS=$((ERRORS + 1))
fi
rm -rf "${OUTPUT_DIR}"

echo ""
echo "--- Checking artifacts not in Git ---"
if git -C "${ROOT_DIR}" ls-files | grep -q "^artifacts/monthly-reports/"; then
    echo -e "${RED}[FAIL]${NC} artifacts/monthly-reports/ should NOT be tracked by Git"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}[OK]${NC} artifacts/monthly-reports/ is correctly ignored by Git"
fi

echo ""
echo "--- Checking required CLI args ---"
if bash "${SCRIPT}" --help 2>&1 | grep -q "Usage"; then
    echo -e "${GREEN}[OK]${NC} --help works"
else
    echo -e "${RED}[FAIL]${NC} --help broken"
    ERRORS=$((ERRORS + 1))
fi

for arg in "--client-id" "--email" "--month" "--output-dir" "--include-technical-details"; do
    if bash "${SCRIPT}" --help 2>&1 | grep -F -q -- "${arg}"; then
        echo -e "${GREEN}[OK]${NC} CLI arg documented: ${arg}"
    else
        echo -e "${RED}[FAIL]${NC} CLI arg missing: ${arg}"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
echo "--- Checking no API keys in generated reports ---"
# Generate a temp report and check
TEMP_DIR=$(mktemp -d)
bash "${SCRIPT}" \
    --client-id "00000000-0000-0000-0000-000000000000" \
    --email "security@test.local" \
    --month "2026-05" \
    --output-dir "${TEMP_DIR}" > /dev/null 2>&1 || true
SECRET_PATTERNS=("sk-[a-zA-Z0-9]\{20,\}" "ghp_[a-zA-Z0-9]\{36\}" "-----BEGIN [A-Z ]*PRIVATE KEY-----")
FOUND_SECRET=false
for file in $(find "${TEMP_DIR}" -type f 2>/dev/null); do
    for pat in "${SECRET_PATTERNS[@]}"; do
        if grep -q "${pat}" "${file}" 2>/dev/null; then
            echo -e "${RED}[FAIL]${NC} Secret found in ${file}"
            FOUND_SECRET=true
            ERRORS=$((ERRORS + 1))
        fi
    done
done
${FOUND_SECRET} || echo -e "${GREEN}[OK]${NC} No secrets in generated reports"
rm -rf "${TEMP_DIR}"

echo ""
if [[ ${ERRORS} -eq 0 ]]; then
    echo -e "${GREEN}All validations passed.${NC}"
    exit 0
else
    echo -e "${RED}${ERRORS} validation(s) failed.${NC}"
    exit 1
fi

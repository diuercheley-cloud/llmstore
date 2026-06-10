#!/usr/bin/env bash
# scripts/validators/validate-contract-templates-local.sh
# Validates that contract templates exist and contain required legal notices.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
CONTRACTS_DIR="${ROOT_DIR}/contracts"
ERRORS=0

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== Validating Contract Templates ==="
echo ""

# Required templates
TEMPLATES=(
    "SOW_TEMPLATE.md"
    "SERVICE_AGREEMENT_TEMPLATE.md"
    "SUPPORT_TERMS_TEMPLATE.md"
    "ACCEPTANCE_CRITERIA_TEMPLATE.md"
    "README.md"
)

echo "--- Checking template files exist ---"
for tpl in "${TEMPLATES[@]}"; do
    path="${CONTRACTS_DIR}/${tpl}"
    if [[ -f "${path}" ]]; then
        echo -e "${GREEN}[OK]${NC} ${tpl}"
    else
        echo -e "${RED}[FAIL]${NC} ${tpl} not found"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
echo "--- Checking legal disclaimer in templates ---"
for tpl in "${TEMPLATES[@]}"; do
    path="${CONTRACTS_DIR}/${tpl}"
    if [[ ! -f "${path}" ]]; then
        continue
    fi
    if grep -qi "revisão jurídica\|revisão por assessoria jurídica\|não constitui aconselhamento jurídico\|template genérico" "${path}"; then
        echo -e "${GREEN}[OK]${NC} ${tpl} contains legal disclaimer"
    else
        echo -e "${RED}[FAIL]${NC} ${tpl} is missing legal disclaimer"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
echo "--- Checking local appliance mention ---"
for tpl in SOW_TEMPLATE.md SERVICE_AGREEMENT_TEMPLATE.md SUPPORT_TERMS_TEMPLATE.md ACCEPTANCE_CRITERIA_TEMPLATE.md; do
    path="${CONTRACTS_DIR}/${tpl}"
    if [[ ! -f "${path}" ]]; then
        continue
    fi
    if grep -qi "local appliance\|Local Appliance" "${path}"; then
        echo -e "${GREEN}[OK]${NC} ${tpl} mentions local appliance"
    else
        echo -e "${RED}[FAIL]${NC} ${tpl} does not mention local appliance"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
echo "--- Checking PSP/PIX disclaimer (real payments NOT included) ---"
for tpl in SOW_TEMPLATE.md SERVICE_AGREEMENT_TEMPLATE.md; do
    path="${CONTRACTS_DIR}/${tpl}"
    if [[ ! -f "${path}" ]]; then
        continue
    fi
    if grep -qi "psp/pix\|PSP.*PIX\|pagamentos.*reais\|processamento.*pagamentos" "${path}"; then
        echo -e "${GREEN}[OK]${NC} ${tpl} mentions PSP/PIX limitation"
    else
        echo -e "${RED}[FAIL]${NC} ${tpl} is missing PSP/PIX limitation"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
echo "--- Checking that generated SOWs are NOT in Git ---"
if git -C "${ROOT_DIR}" ls-files | grep -q "^artifacts/contracts/"; then
    echo -e "${RED}[FAIL]${NC} artifacts/contracts/ should NOT be tracked by Git"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}[OK]${NC} artifacts/contracts/ is correctly ignored by Git"
fi

echo ""
echo "--- Checking templates contain no real secrets ---"
SECRET_PATTERNS=("sk-[a-zA-Z0-9]\{20,\}" "ghp_[a-zA-Z0-9]\{36\}" "-----BEGIN [A-Z ]*PRIVATE KEY-----" "[a-zA-Z0-9_+.\-]\+:[a-zA-Z0-9_+.\-]\+@")
for tpl in "${TEMPLATES[@]}"; do
    path="${CONTRACTS_DIR}/${tpl}"
    if [[ ! -f "${path}" ]]; then
        continue
    fi
    for pat in "${SECRET_PATTERNS[@]}"; do
        if grep -q "${pat}" "${path}" 2>/dev/null; then
            echo -e "${RED}[FAIL]${NC} ${tpl} may contain secrets (matched pattern)"
            ERRORS=$((ERRORS + 1))
        fi
    done
done
echo -e "${GREEN}[OK]${NC} No secrets detected in templates"

echo ""
if [[ ${ERRORS} -eq 0 ]]; then
    echo -e "${GREEN}All validations passed.${NC}"
    exit 0
else
    echo -e "${RED}${ERRORS} validation(s) failed.${NC}"
    exit 1
fi

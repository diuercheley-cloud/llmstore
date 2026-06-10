#!/usr/bin/env bash
# scripts/validators/validate-paid-implementation-checklist.sh
# Validates the paid implementation checklist template and generation.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
DOC="${ROOT_DIR}/docs/PAID_IMPLEMENTATION_CHECKLIST.md"
ERRORS=0

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== Validating Paid Implementation Checklist ==="
echo ""

echo "--- Checking document exists ---"
if [[ -f "${DOC}" ]]; then
    echo -e "${GREEN}[OK]${NC} PAID_IMPLEMENTATION_CHECKLIST.md exists"
else
    echo -e "${RED}[FAIL]${NC} PAID_IMPLEMENTATION_CHECKLIST.md not found"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "--- Checking required sections ---"
REQUIRED_SECTIONS=(
    "Antes da Implantação"
    "Requisitos de Hardware"
    "Requisitos de Acesso"
    "Responsabilidades do Cliente"
    "Responsabilidades do Fornecedor"
    "Backup Inicial"
    "Instalação"
    "Configuração"
    "Modelos"
    "Segurança"
    "Testes de Aceite"
    "Treinamento do Operador"
    "Entrega Final"
    "Pós-Implantação"
    "Assinaturas"
)
for section in "${REQUIRED_SECTIONS[@]}"; do
    if grep -qi "${section}" "${DOC}" 2>/dev/null; then
        echo -e "${GREEN}[OK]${NC} Section found: ${section}"
    else
        echo -e "${RED}[FAIL]${NC} Missing section: ${section}"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
echo "--- Checking generation script exists ---"
SCRIPT="${ROOT_DIR}/scripts/validators/paid-implementation-checklist-local.sh"
if [[ -x "${SCRIPT}" ]]; then
    echo -e "${GREEN}[OK]${NC} script exists and is executable"
else
    echo -e "${RED}[FAIL]${NC} script missing or not executable"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "--- Testing checklist generation ---"
OUTPUT_DIR=$(mktemp -d)
if bash "${SCRIPT}" --company-name "Validate Corp" --operator-name "Validator" --output-dir "${OUTPUT_DIR}" > /dev/null 2>&1; then
    echo -e "${GREEN}[OK]${NC} Checklist generation succeeded"
    # Check for files
    MD_FILE=$(find "${OUTPUT_DIR}" -name "implementation-checklist.md" 2>/dev/null | head -1)
    JSON_FILE=$(find "${OUTPUT_DIR}" -name "implementation-checklist.json" 2>/dev/null | head -1)
    if [[ -n "${MD_FILE}" ]]; then
        echo -e "${GREEN}[OK]${NC} implementation-checklist.md generated"
    else
        echo -e "${RED}[FAIL]${NC} implementation-checklist.md not found"
        ERRORS=$((ERRORS + 1))
    fi
    if [[ -n "${JSON_FILE}" ]]; then
        echo -e "${GREEN}[OK]${NC} implementation-checklist.json generated"
    else
        echo -e "${RED}[FAIL]${NC} implementation-checklist.json not found"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${RED}[FAIL]${NC} Checklist generation failed"
    ERRORS=$((ERRORS + 1))
fi
rm -rf "${OUTPUT_DIR}"

echo ""
echo "--- Checking backup mention ---"
if grep -qi "backup" "${DOC}" 2>/dev/null; then
    echo -e "${GREEN}[OK]${NC} Document mentions backup"
else
    echo -e "${RED}[FAIL]${NC} Document does not mention backup"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "--- Checking acceptance criteria mention ---"
if grep -qi "critério de aceite\|aceite\|acceptance\|Testes de Aceite" "${DOC}" 2>/dev/null; then
    echo -e "${GREEN}[OK]${NC} Document mentions acceptance criteria"
else
    echo -e "${RED}[FAIL]${NC} Document does not mention acceptance criteria"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "--- Checking PSP/PIX disclaimer ---"
if grep -qi "psp\|pix\|pagamentos reais\|processamento de pagamentos" "${DOC}" 2>/dev/null; then
    echo -e "${GREEN}[OK]${NC} Document mentions PSP/PIX limitation"
else
    echo -e "${RED}[FAIL]${NC} Document missing PSP/PIX limitation"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "--- Checking that artifacts are NOT in Git ---"
if git -C "${ROOT_DIR}" ls-files | grep -q "^artifacts/implementation-checklists/"; then
    echo -e "${RED}[FAIL]${NC} artifacts/implementation-checklists/ should NOT be tracked by Git"
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}[OK]${NC} artifacts/implementation-checklists/ is correctly ignored by Git"
fi

echo ""
echo "--- Checking document contains no real secrets ---"
SECRET_PATTERNS=("sk-[a-zA-Z0-9]\{20,\}" "ghp_[a-zA-Z0-9]\{36\}" "-----BEGIN [A-Z ]*PRIVATE KEY-----" "[a-zA-Z0-9_+.\-]\+:[a-zA-Z0-9_+.\-]\+@")
for pat in "${SECRET_PATTERNS[@]}"; do
    if grep -q "${pat}" "${DOC}" 2>/dev/null; then
        echo -e "${RED}[FAIL]${NC} Document may contain secrets"
        ERRORS=$((ERRORS + 1))
    fi
done
echo -e "${GREEN}[OK]${NC} No secrets detected in document"

echo ""
echo "--- Checking status definitions exist ---"
for status in "NOT_STARTED" "IN_PROGRESS" "BLOCKED" "READY_FOR_ACCEPTANCE" "ACCEPTED"; do
    if grep -qi "${status}" "${DOC}" 2>/dev/null; then
        echo -e "${GREEN}[OK]${NC} Status defined: ${status}"
    else
        echo -e "${RED}[WARN]${NC} Status may be missing: ${status}"
    fi
done

echo ""
if [[ ${ERRORS} -eq 0 ]]; then
    echo -e "${GREEN}All validations passed.${NC}"
    exit 0
else
    echo -e "${RED}${ERRORS} validation(s) failed.${NC}"
    exit 1
fi

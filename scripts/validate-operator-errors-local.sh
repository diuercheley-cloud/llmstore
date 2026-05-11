#!/usr/bin/env bash
# Validate Operator Errors implementation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

# Load library
LIB_PATH="${SCRIPT_DIR}/lib/operator-errors.sh"
if [[ ! -f "${LIB_PATH}" ]]; then
    echo "[ERROR] Library not found: ${LIB_PATH}"
    exit 1
fi
source "${LIB_PATH}"

CATALOG_PATH="${ROOT_DIR}/docs/OPERATOR_ERROR_CODES.md"
if [[ ! -f "${CATALOG_PATH}" ]]; then
    operator_error "VALIDATION_FAILED" "Catálogo de erros não encontrado." "Crie o arquivo ${CATALOG_PATH}."
    exit 1
fi

echo "--- Validating scripts usage ---"
SCRIPTS=(
    "install-local-appliance.sh"
    "configure-local-wizard.sh"
    "first-run-local.sh"
    "validate-local-production-full.sh"
    "security-report-local.sh"
    "production-readiness-local.sh"
    "upgrade-local.sh"
    "rollback-local.sh"
    "post-upgrade-smoke-local.sh"
    "release-local-production.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [[ ! -f "${SCRIPT_DIR}/${script}" ]]; then
        operator_warning "VALIDATION_FAILED" "Script não encontrado: ${script}" "Verifique se o script foi movido ou deletado."
        continue
    fi
    
    # Check if sources library or common.sh (which sources library)
    if grep -q "operator-errors.sh" "${SCRIPT_DIR}/${script}" || grep -q "source.*common.sh" "${SCRIPT_DIR}/${script}"; then
        echo "[OK] ${script} uses operator-errors"
    else
        operator_error "VALIDATION_FAILED" "Script ${script} não parece usar operator-errors.sh" "Adicione o source da biblioteca ou do common.sh no script."
        exit 1
    fi
done

echo "--- Validating redaction in messages ---"
TEST_API_KEY="$(printf '%s%s' 'abcdefghijklmnop' 'qrstuvwxyz12')"
TEST_MSG="Secret: API_KEY=${TEST_API_KEY}"
MASKED=$(mask_sensitive "${TEST_MSG}")
if [[ "${MASKED}" == *"${TEST_API_KEY}"* ]]; then
    operator_error "SECURITY_FAILED" "A máscara de sensíveis falhou." "Revise a função mask_sensitive em scripts/lib/operator-errors.sh."
    exit 1
else
    echo "[OK] mask_sensitive is working: ${MASKED}"
fi

echo "--- Simulating an error ---"
operator_error "TEST_CODE" "Esta é uma simulação de erro para validação." "Nenhuma ação necessária, isto é apenas um teste." "Detalhe técnico simulado."

operator_success "Validação de operator-errors concluída com sucesso!"

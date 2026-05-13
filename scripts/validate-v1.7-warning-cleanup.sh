#!/usr/bin/env bash
# validate-v1.7-warning-cleanup.sh
# Valida se o processo de limpeza de warnings foi concluído com sucesso.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

log() { echo "[INFO] $1"; }
pass() { echo "  [PASS] $1"; }
fail() { echo "  [FAIL] $1"; exit 1; }

log "Iniciando validação de limpeza de warnings v1.7.1..."

# 1. Verificar scripts
[[ -x "${SCRIPT_DIR}/diagnose-v1.7-warnings.sh" ]] || fail "diagnose-v1.7-warnings.sh não é executável"
pass "Script de diagnóstico existe"

# 2. Verificar documentação
[[ -f "${ROOT_DIR}/docs/V1_7_1_WARNING_CLEANUP.md" ]] || fail "docs/V1_7_1_WARNING_CLEANUP.md não existe"
pass "Documentação de cleanup existe"

# 3. Rodar diagnóstico mais recente
bash "${SCRIPT_DIR}/diagnose-v1.7-warnings.sh" > /dev/null
LATEST_CLEANUP=$(ls -dt "${ROOT_DIR}/artifacts/v1.7-warning-cleanup"/* 2>/dev/null | head -n 1)
[[ -f "${LATEST_CLEANUP}/warnings.json" ]] || fail "Relatório JSON de warnings não gerado"
pass "Relatório de diagnóstico gerado"

# 4. Verificar se há warnings fixable não tratados
FIXABLE_COUNT=$(python3 -c "import json; data=json.load(open('${LATEST_CLEANUP}/warnings.json')); print(sum(1 for w in data['warnings'] if w['classification'] == 'fixable'))")
if [[ "$FIXABLE_COUNT" -gt 0 ]]; then
    fail "Ainda existem ${FIXABLE_COUNT} warnings classificados como 'fixable'!"
fi
pass "Nenhum warning 'fixable' pendente"

# 5. Verificar status final na validação local
LATEST_VAL=$(ls -dt "${ROOT_DIR}/artifacts/v1.7-final-validation"/* 2>/dev/null | head -n 1)
[[ -f "${LATEST_VAL}/v1.7-final-validation.json" ]] || fail "Relatório de validação final não encontrado"

STATUS=$(python3 -c "import json; data=json.load(open('${LATEST_VAL}/v1.7-final-validation.json')); print(data['final_status'])")
if [[ "$STATUS" == "V1_7_READY" ]] || [[ "$STATUS" == "V1_7_READY_WITH_ACCEPTED_WARNINGS" ]]; then
    pass "Status final adequado: ${STATUS}"
else
    fail "Status final inadequado: ${STATUS}. Esperado V1_7_READY ou V1_7_READY_WITH_ACCEPTED_WARNINGS"
fi

# 6. Rodar testes pytest
log "Rodando testes de política de warnings..."
"${ROOT_DIR}/.venv/bin/python" -m pytest \
    "${ROOT_DIR}/tests/test_v1_7_warning_diagnostics.py" \
    "${ROOT_DIR}/tests/test_v1_7_warning_cleanup.py" \
    "${ROOT_DIR}/tests/test_v1_7_final_warnings_policy.py" -q

pass "Testes de política concluídos com sucesso"

log "Limpeza de warnings validada com sucesso! [READY]"

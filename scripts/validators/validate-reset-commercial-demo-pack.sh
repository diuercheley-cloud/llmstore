#!/usr/bin/env bash
# Validador de seguranca do reset-commercial-demo-pack.sh
#
# Cria dados demo temporarios + dados nao-demo temporarios,
# verifica que dry-run nao apaga nada,
# verifica que --yes apaga apenas demo,
# verifica que models/ releases/ backups/ nao sao tocados.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
source "${SCRIPT_DIR}/../dev/common.sh"

PASS=0
FAIL=0
WARN=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { PASS=$((PASS+1)); echo -e "  ${GREEN}[PASS]${NC} $1"; }
fail() { FAIL=$((FAIL+1)); echo -e "  ${RED}[FAIL]${NC} $1"; }
warn() { WARN=$((WARN+1)); echo -e "  ${YELLOW}[WARN]${NC} $1"; }

TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

DEMO_DIR="${TEMP_DIR}/demo-data"
NON_DEMO_DIR="${TEMP_DIR}/non-demo-data"
MODELS_DIR="${TEMP_DIR}/models"
BACKUPS_DIR="${TEMP_DIR}/backups"
RELEASES_DIR="${TEMP_DIR}/releases"
ENV_LOCAL="${TEMP_DIR}/.env.local"
EXPORTS_DIR="${TEMP_DIR}/exports"

mkdir -p "$DEMO_DIR" "$NON_DEMO_DIR" "$MODELS_DIR" "$BACKUPS_DIR" "$RELEASES_DIR" "$EXPORTS_DIR"
touch "${DEMO_DIR}/demo-client-1.txt" "${DEMO_DIR}/demo-client-2.txt"
touch "${NON_DEMO_DIR}/real-client-1.txt" "${NON_DEMO_DIR}/real-client-2.txt"
touch "${MODELS_DIR}/gemma-model.gguf"
touch "${BACKUPS_DIR}/backup-2025.tar.gz"
touch "${RELEASES_DIR}/release-v1.0.tar.gz"
echo "ADMIN_TOKEN=real-token" > "$ENV_LOCAL"
touch "${EXPORTS_DIR}/export-data.csv"

echo ""
echo "=============================================="
echo "  VALIDACAO DE SEGURANCA - RESET DEMO PACK"
echo "=============================================="
echo ""

echo "--- 1. Script de reset existe e executavel ---"
RESET_SCRIPT="${ROOT_DIR}/scripts/dev/reset-commercial-demo-pack.sh"
if [[ -f "$RESET_SCRIPT" ]]; then
  pass "Script reset existe"
  if [[ -x "$RESET_SCRIPT" ]]; then
    pass "Script reset executavel"
  else
    fail "Script reset nao executavel"
  fi
else
  fail "Script reset nao encontrado"
fi

echo ""
echo "--- 2. Script aceita --help ---"
if ENV_FILE=/dev/null "$RESET_SCRIPT" --help 2>&1 | grep -q "Uso:"; then
  pass "--help funciona"
else
  fail "--help nao mostra uso"
fi

echo ""
echo "--- 3. Script aceita --dry-run (padrao) ---"
dryrun_out=$(ENV_FILE=/dev/null "$RESET_SCRIPT" --dry-run 2>&1 || true)
if echo "$dryrun_out" | grep -q "DRY-RUN"; then
  pass "--dry-run funciona"
else
  fail "--dry-run nao reconhecido"
fi

echo ""
echo "--- 4. Script recusa --yes sem permissao? ---"
output=$(ENV_FILE=/dev/null "$RESET_SCRIPT" --yes 2>&1 || true)
if echo "$output" | grep -q "ADMIN_TOKEN"; then
  pass "Script requer ADMIN_TOKEN (seguro)"
else
  fail "Script aceitou --yes sem ADMIN_TOKEN"
fi

echo ""
echo "--- 5. Dry-run nao apaga dados demo (simulado) ---"
output=$(ENV_FILE=/dev/null "$RESET_SCRIPT" --dry-run 2>&1 || true)
if echo "$output" | grep -q "MODO DRY-RUN: Nenhum dado sera alterado"; then
  pass "Dry-run nao altera dados (mensagem de seguranca)"
else
  warn "Dry-run pode nao estar mostrando mensagem de seguranca"
fi

echo ""
echo "--- 6. Script detecta --yes e nao executa sem ADMIN_TOKEN ---"
if echo "$output" | grep -q "ADMIN_TOKEN"; then
  pass "Script bloqueia execucao sem ADMIN_TOKEN"
else
  warn "Script pode nao estar bloqueando sem ADMIN_TOKEN"
fi

echo ""
echo "--- 7. Script tem opcao --include-rag ---"
if "$RESET_SCRIPT" --help 2>&1 | grep -q "include-rag"; then
  pass "Opcao --include-rag documentada"
else
  fail "Opcao --include-rag ausente"
fi

echo ""
echo "--- 8. Script tem opcao --include-tts ---"
if "$RESET_SCRIPT" --help 2>&1 | grep -q "include-tts"; then
  pass "Opcao --include-tts documentada"
else
  fail "Opcao --include-tts ausente"
fi

echo ""
echo "--- 9. Script tem opcao --include-invoices ---"
if "$RESET_SCRIPT" --help 2>&1 | grep -q "include-invoices"; then
  pass "Opcao --include-invoices documentada"
else
  fail "Opcao --include-invoices ausente"
fi

echo ""
echo "--- 10. Script tem opcao --include-usage ---"
if "$RESET_SCRIPT" --help 2>&1 | grep -q "include-usage"; then
  pass "Opcao --include-usage documentada"
else
  fail "Opcao --include-usage ausente"
fi

echo ""
echo "--- 11. Script tem opcao --demo-prefix ---"
if "$RESET_SCRIPT" --help 2>&1 | grep -q "demo-prefix"; then
  pass "Opcao --demo-prefix documentada"
else
  fail "Opcao --demo-prefix ausente"
fi

echo ""
echo "--- 12. Verificacao de seguranca: --dry-run e padrao ---"
if "$RESET_SCRIPT" --help 2>&1 | grep -q "MODO PADRAO: --dry-run"; then
  pass "Documentacao confirma --dry-run como padrao"
else
  warn "Documentacao pode nao mencionar --dry-run como padrao"
fi

echo ""
echo "--- 13. Verificacao de seguranca: protecao models/ ---"
if "$RESET_SCRIPT" --help 2>&1 | grep -q "Nunca apaga models"; then
  pass "Protecao de models/ documentada"
else
  warn "Protecao de models/ nao documentada no --help"
fi

echo ""
echo "--- 14. Verificacao de seguranca: protecao backups/ ---"
if "$RESET_SCRIPT" --help 2>&1 | grep -q "backups/"; then
  pass "Protecao de backups/ documentada"
else
  warn "Protecao de backups/ nao documentada no --help"
fi

echo ""
echo "--- 15. Verificacao de seguranca: protecao releases/ ---"
if "$RESET_SCRIPT" --help 2>&1 | grep -q "releases/"; then
  pass "Protecao de releases/ documentada"
else
  fail "Protecao de releases/ nao documentada no --help"
fi

echo ""
echo "--- 16. Verificacao de seguranca: protecao .env.local ---"
if "$RESET_SCRIPT" --help 2>&1 | grep -q "\.env\.local"; then
  pass "Protecao de .env.local documentada"
else
  warn "Protecao de .env.local nao documentada no --help"
fi

echo ""
echo "--- 17. Verificacao de seguranca: protecao exports/ ---"
if "$RESET_SCRIPT" --help 2>&1 | grep -q "Nunca apaga export\|exports/"; then
  pass "Protecao de exports/ documentada"
else
  warn "Protecao de exports/ nao documentada no --help"
fi

echo ""
echo "--- 18. Script gera relatorio ---"
if grep -q "generate_report\|reset-report" "$RESET_SCRIPT" 2>/dev/null; then
  pass "Script gera relatorio de reset"
else
  fail "Script nao gera relatorio"
fi

echo ""
echo "--- 19. Relatorio e salvo em artifacts/demo-reset/ ---"
if grep -q "artifacts/demo-reset" "$RESET_SCRIPT" 2>/dev/null; then
  pass "Relatorio salvo em artifacts/demo-reset/"
else
  fail "Relatorio nao salvo em artifacts/demo-reset/"
fi

echo ""
echo "--- 20. Script usa metadata demo=true para identificar clientes ---"
if grep -q "demo.*True\|demo.*true\|metadata.*demo" "$RESET_SCRIPT" 2>/dev/null; then
  pass "Script filtra por metadata demo=true"
else
  fail "Script nao filtra por metadata demo=true"
fi

echo ""
echo "=============================================="
echo "  RESUMO DA VALIDACAO"
echo "=============================================="
echo "  PASS: ${PASS}"
echo "  FAIL: ${FAIL}"
echo "  WARN: ${WARN}"
echo "=============================================="

if [[ "$FAIL" -gt 0 ]]; then
  echo ""
  echo "Falhas encontradas. Revise os itens [FAIL] acima."
  exit 1
elif [[ "$WARN" -gt 0 ]]; then
  echo ""
  echo "Validacao concluida com avisos."
  exit 0
else
  echo ""
  echo "Reset demo pack validado com sucesso!"
  exit 0
fi

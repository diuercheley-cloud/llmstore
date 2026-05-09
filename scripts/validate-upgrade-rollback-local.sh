#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env
cd "${ROOT_DIR}"

echo "--------------------------------------------------------"
echo "Validando scripts de Upgrade e Rollback"
echo "--------------------------------------------------------"

# 1. Help
echo "[validate] Testando --help..."
./scripts/upgrade-local.sh --help > /dev/null
./scripts/rollback-local.sh --help > /dev/null
echo "[validate] OK"

# 2. Dry-run upgrade
CURRENT_VERSION="$(tr -d '\n' < "${ROOT_DIR}/VERSION" || echo "v1.0.0")"
echo "[validate] Testando dry-run upgrade para versão atual (${CURRENT_VERSION})..."
if ! ./scripts/upgrade-local.sh --to-version "${CURRENT_VERSION}" --dry-run; then
  echo "[validate][error] Dry-run upgrade falhou."
  exit 1
fi
echo "[validate] OK"

# 3. Dry-run rollback
echo "[validate] Testando dry-run rollback para versão atual (${CURRENT_VERSION})..."
MOCK_BACKUP="artifacts/backups-local/mock-validate-$(date +%Y%m%dT%H%M%S)"
mkdir -p "${MOCK_BACKUP}"
if ! ./scripts/rollback-local.sh --to-version "${CURRENT_VERSION}" --backup-id "${MOCK_BACKUP}" --dry-run --yes; then
  echo "[validate][error] Dry-run rollback falhou."
  rm -rf "${MOCK_BACKUP}"
  exit 1
fi
rm -rf "${MOCK_BACKUP}"
echo "[validate] OK"

# 4. Missing arguments
echo "[validate] Testando falta de argumentos..."
if ./scripts/upgrade-local.sh > /dev/null 2>&1; then
  echo "[validate][error] upgrade-local.sh deveria ter falhado sem --to-version"
  exit 1
fi
if ./scripts/rollback-local.sh > /dev/null 2>&1; then
  echo "[validate][error] rollback-local.sh deveria ter falhado sem argumentos"
  exit 1
fi
echo "[validate] OK"

# 5. Validation of security guarantees
echo "[validate] Verificando garantias de segurança..."
# Check if scripts have safety checks (grep for git diff-index)
if ! grep -q "git diff-index" scripts/upgrade-local.sh; then
  echo "[validate][error] upgrade-local.sh falta verificação de working tree clean"
  exit 1
fi
if ! grep -q "git diff-index" scripts/rollback-local.sh; then
  echo "[validate][error] rollback-local.sh falta verificação de working tree clean"
  exit 1
fi
if ! grep -q "ROLLBACK LOCAL" scripts/rollback-local.sh; then
  echo "[validate][error] rollback-local.sh falta confirmação forte"
  exit 1
fi

echo "--------------------------------------------------------"
echo "[validate] Todos os testes de validação básica passaram!"
echo "--------------------------------------------------------"

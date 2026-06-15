#!/usr/bin/env bash
set -euo pipefail

# Resolve symlink if BASH_SOURCE[0] is a symlink
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env
cd "${ROOT_DIR}"

# Default values
TO_VERSION=""
BACKUP_ID=""
SKIP_GIT_CHECK=false
NO_BUILD=false
AUTO_CONFIRM=false
DRY_RUN=false

usage() {
  cat <<EOF
Uso: ./scripts/dev/rollback-local.sh [OPÇÕES]

Opções:
  --to-version vX.Y.Z    Versão para a qual retornar (obrigatório)
  --backup-id path       Caminho do backup para restaurar (obrigatório)
  --skip-git-check       Pula a verificação de working tree limpa
  --no-build             Pula o docker compose build
  -y, --yes              Pula confirmações
  --dry-run              Apenas mostra o que seria feito
  -h, --help             Mostra esta mensagem

Este script realiza o rollback da stack local para uma versão anterior.
Ele exige confirmação forte, troca a versão (git checkout), restaura o backup,
sobe os serviços e valida com smoke tests.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --to-version) TO_VERSION="$2"; shift ;;
    --backup-id) BACKUP_ID="$2"; shift ;;
    --skip-git-check) SKIP_GIT_CHECK=true ;;
    --no-build) NO_BUILD=true ;;
    -y|--yes) AUTO_CONFIRM=true ;;
    --dry-run) DRY_RUN=true ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Erro: Argumento desconhecido $1"; usage; exit 1 ;;
  esac
  shift
done

if [[ -z "${TO_VERSION}" ]] || [[ -z "${BACKUP_ID}" ]]; then
  operator_error "VALIDATION_FAILED" "Os parâmetros --to-version e --backup-id são obrigatórios." "Informe a versão e o diretório de backup, por exemplo: --to-version v1.6.1 --backup-id artifacts/backups-local/..."
  usage
  exit 1
fi

if [[ ! -d "${BACKUP_ID}" ]] && [[ "${DRY_RUN}" == "false" ]]; then
  operator_error "RESTORE_FAILED" "O diretório de backup não foi encontrado." "Verifique se o caminho informado em --backup-id está correto." "Diretório ${BACKUP_ID} não existe."
  exit 1
fi

# 1. Safety checks
if [[ "${DRY_RUN}" == "false" ]]; then
  if [[ "${SKIP_GIT_CHECK}" == "false" ]]; then
    if ! git diff-index --quiet HEAD --; then
      operator_error "VALIDATION_FAILED" "O working tree do Git possui alterações não confirmadas." "Faça commit ou stash das suas alterações antes de prosseguir com o rollback." "git diff-index falhou."
      exit 1
    fi
  fi
fi

# 2. Confirmation
if [[ "${AUTO_CONFIRM}" != "true" ]]; then
  echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
  echo "ATENCAO: VOCE ESTA PRESTES A REALIZAR UM ROLLBACK LOCAL"
  echo "Isso irá SUBSTITUIR os dados atuais pelo backup informado."
  echo "Versão alvo: ${TO_VERSION}"
  echo "Backup ID: ${BACKUP_ID}"
  echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
  printf "Para confirmar, digite exatamente: ROLLBACK LOCAL %s\n" "${TO_VERSION}"
  read -r response
  if [[ "${response}" != "ROLLBACK LOCAL ${TO_VERSION}" ]]; then
    echo "[rollback] Abortado pelo usuário (confirmação incorreta)."
    exit 0
  fi
fi

# 3. Stop services
echo "[rollback] Parando serviços para garantir estado limpo..."
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] dc down"
else
  dc down
fi

# 4. Checkout target version
echo "[rollback] Trocando para versão ${TO_VERSION}..."
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] git checkout ${TO_VERSION}"
else
  if ! git checkout "${TO_VERSION}"; then
    operator_error "ROLLBACK_FAILED" "Falha ao trocar para a versão ${TO_VERSION}." "Verifique se a tag ou branch '${TO_VERSION}' existe no repositório." "git checkout falhou."
    exit 1
  fi
fi

# 5. Restore backup
echo "[rollback] Restaurando backup a partir de: ${BACKUP_ID}"
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] ./scripts/backup/restore-local.sh --yes ${BACKUP_ID}"
else
  ./scripts/backup/restore-local.sh --yes "${BACKUP_ID}"
  echo "[rollback] Backup restaurado: ${BACKUP_ID}"
fi

# 6. Build and Up
if [[ "${NO_BUILD}" == "false" ]]; then
  echo "[rollback] Construindo imagens da versão ${TO_VERSION}..."
  if [[ "${DRY_RUN}" == "true" ]]; then
    echo "[dry-run] dc build"
  else
    dc build
  fi
fi

echo "[rollback] Subindo stack..."
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] dc up -d"
else
  dc up -d
fi

# 7. Smoke tests
SMOKE_STATUS="success"
echo "[rollback] Rodando smoke tests pós-rollback..."
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] ./scripts/validators/post-upgrade-smoke-local.sh"
else
  if ! ./scripts/validators/post-upgrade-smoke-local.sh; then
    SMOKE_STATUS="failed"
  fi
fi

# 8. Report
ROLLBACK_TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
REPORT_DIR="${ROOT_DIR}/artifacts/rollbacks/${ROLLBACK_TIMESTAMP}"
if [[ "${DRY_RUN}" == "false" ]]; then
  mkdir -p "${REPORT_DIR}"
  REPORT_FILE_JSON="${REPORT_DIR}/rollback-report.json"
  REPORT_FILE_MD="${REPORT_DIR}/rollback-report.md"

  cat <<EOF > "${REPORT_FILE_JSON}"
{
  "timestamp": "${ROLLBACK_TIMESTAMP}",
  "to_version": "${TO_VERSION}",
  "backup_id": "${BACKUP_ID}",
  "status": "${SMOKE_STATUS}"
}
EOF

  cat <<EOF > "${REPORT_FILE_MD}"
# Rollback Report - ${ROLLBACK_TIMESTAMP}

- **To Version:** ${TO_VERSION}
- **Backup ID (used):** ${BACKUP_ID}
- **Status:** ${SMOKE_STATUS}
- **Date:** $(date)

Rollback local concluído com status de smoke test: ${SMOKE_STATUS}.
EOF

  if [[ "${SMOKE_STATUS}" == "failed" ]]; then
    operator_error "ROLLBACK_FAILED" "O rollback foi concluído, mas os testes de fumaça (smoke tests) falharam!" "Revise os logs e considere restaurar o backup manualmente ou tentar outro rollback." "post-upgrade-smoke-local.sh falhou."
    exit 1
  fi

  echo "--------------------------------------------------------"
  operator_success "Rollback da stack concluído com sucesso!"
  add_next_step "Acesse o sistema em ${BASE_URL:-http://localhost:18080}"
  add_next_step "Revise o relatório de rollback: ${REPORT_FILE_MD}"
  print_next_steps
  echo "--------------------------------------------------------"
else
  echo "--------------------------------------------------------"
  operator_success "Simulação de rollback (dry-run) concluída com sucesso."
  echo "--------------------------------------------------------"
fi

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
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
Uso: ./scripts/rollback-local.sh [OPÇÕES]

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
  echo "Erro: --to-version e --backup-id são obrigatórios."
  usage
  exit 1
fi

if [[ ! -d "${BACKUP_ID}" ]] && [[ "${DRY_RUN}" == "false" ]]; then
  echo "Erro: Backup ID (diretório) não encontrado: ${BACKUP_ID}"
  exit 1
fi

# 1. Safety checks
if [[ "${DRY_RUN}" == "false" ]]; then
  if [[ "${SKIP_GIT_CHECK}" == "false" ]]; then
    if ! git diff-index --quiet HEAD --; then
      echo "[rollback][error] Working tree is dirty. Please commit or stash changes." >&2
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
    echo "[rollback][error] Falha ao trocar para a versão ${TO_VERSION}." >&2
    exit 1
  fi
fi

# 5. Restore backup
echo "[rollback] Restaurando backup..."
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] ./scripts/restore-local.sh --yes ${BACKUP_ID}"
else
  ./scripts/restore-local.sh --yes "${BACKUP_ID}"
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
echo "[rollback] Rodando smoke tests pós-rollback..."
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] ./scripts/post-upgrade-smoke-local.sh"
else
  ./scripts/post-upgrade-smoke-local.sh || {
    echo "[rollback][error] Smoke tests FAILED after rollback!"
    exit 1
  }
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
  "status": "success"
}
EOF

  cat <<EOF > "${REPORT_FILE_MD}"
# Rollback Report - ${ROLLBACK_TIMESTAMP}

- **To Version:** ${TO_VERSION}
- **Backup ID:** ${BACKUP_ID}
- **Status:** Success
- **Date:** $(date)

Rollback local concluído com sucesso.
EOF

  echo "--------------------------------------------------------"
  echo "[rollback] Rollback concluído com sucesso!"
  echo "[rollback] Relatório: ${REPORT_FILE_MD}"
  echo "--------------------------------------------------------"
else
  echo "--------------------------------------------------------"
  echo "[rollback] Dry-run concluído com sucesso."
  echo "--------------------------------------------------------"
fi

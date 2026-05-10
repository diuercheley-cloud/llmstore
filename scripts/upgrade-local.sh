#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env
cd "${ROOT_DIR}"

# Default values
TO_VERSION=""
FROM_VERSION=""
SKIP_BACKUP=false
SKIP_GIT_CHECK=false
NO_BUILD=false
AUTO_CONFIRM=false
DRY_RUN=false

usage() {
  cat <<EOF
Uso: ./scripts/upgrade-local.sh [OPÇÕES]

Opções:
  --to-version vX.Y.Z    Versão alvo para upgrade (obrigatório)
  --from-version vX.Y.Z  Versão atual (opcional, detectada se omitida)
  --skip-backup          Pula a criação de backup antes do upgrade
  --skip-git-check       Pula a verificação de working tree limpa
  --no-build             Pula o docker compose build
  -y, --yes              Pula confirmações
  --dry-run              Apenas mostra o que seria feito
  -h, --help             Mostra esta mensagem

Este script realiza o upgrade da stack local para uma nova versão.
Ele cria um backup, troca a versão (git checkout), reconstrói as imagens,
sobe os serviços, roda migrations e valida com smoke tests.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --to-version) TO_VERSION="$2"; shift ;;
    --from-version) FROM_VERSION="$2"; shift ;;
    --skip-backup) SKIP_BACKUP=true ;;
    --skip-git-check) SKIP_GIT_CHECK=true ;;
    --no-build) NO_BUILD=true ;;
    -y|--yes) AUTO_CONFIRM=true ;;
    --dry-run) DRY_RUN=true ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Erro: Argumento desconhecido $1"; usage; exit 1 ;;
  esac
  shift
done

if [[ -z "${TO_VERSION}" ]]; then
  echo "Erro: --to-version é obrigatório."
  usage
  exit 1
fi

# 1. Detect current version
CURRENT_VERSION="$(tr -d '\n' < "${ROOT_DIR}/VERSION" || echo "unknown")"
FROM_VERSION="${FROM_VERSION:-${CURRENT_VERSION}}"

echo "--------------------------------------------------------"
echo "Upgrade Workflow: ${FROM_VERSION} -> ${TO_VERSION}"
echo "--------------------------------------------------------"

# 2. Safety checks
if [[ "${DRY_RUN}" == "false" ]]; then
  if [[ "${SKIP_GIT_CHECK}" == "false" ]]; then
    if ! git diff-index --quiet HEAD --; then
      echo "[upgrade][error] Working tree is dirty. Please commit or stash changes." >&2
      exit 1
    fi
  fi

  echo "[upgrade] Rodando check-secrets..."
  if ! ./scripts/check-secrets.sh --all; then
    echo "[upgrade][error] Secrets check failed. Please remove secrets before upgrade." >&2
    exit 1
  fi
fi

# 3. Create backup
BACKUP_ID="none"
if [[ "${SKIP_BACKUP}" == "false" ]]; then
  echo "[upgrade] Criando backup de segurança..."
  if [[ "${DRY_RUN}" == "true" ]]; then
    echo "[dry-run] ./scripts/backup-local.sh"
    BACKUP_ID="dry-run-backup-$(date +%Y%m%dT%H%M%S)"
  else
    BACKUP_OUTPUT="$(./scripts/backup-local.sh --include-rag-files)"
    BACKUP_ID="$(echo "${BACKUP_OUTPUT}" | grep "dir=" | cut -d= -f2)"
    echo "[upgrade] Backup criado em: ${BACKUP_ID}"
  fi
else
  echo "[upgrade][warn] Backup ignorado (--skip-backup)."
fi

# 4. Checkout target version
echo "[upgrade] Trocando para versão ${TO_VERSION}..."
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] git checkout ${TO_VERSION}"
else
  if ! git checkout "${TO_VERSION}"; then
    echo "[upgrade][error] Falha ao trocar para a versão ${TO_VERSION}." >&2
    exit 1
  fi
fi

# 5. Build and Up
if [[ "${NO_BUILD}" == "false" ]]; then
  echo "[upgrade] Construindo imagens..."
  if [[ "${DRY_RUN}" == "true" ]]; then
    echo "[dry-run] dc build"
  else
    dc build
  fi
fi

echo "[upgrade] Subindo stack..."
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] dc up -d"
else
  dc up -d
fi

# 6. Migrations
echo "[upgrade] Validando migrations antes de aplicar..."
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] ./scripts/validate-migrations-local.sh"
else
  ./scripts/validate-migrations-local.sh
fi

echo "[upgrade] Verificando banco de dados e rodando migrations..."
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] dc exec -T control-plane alembic upgrade head"
else
  # Wait for DB to be ready
  for _ in $(seq 1 30); do
    if dc exec -T postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
  dc exec -T control-plane alembic upgrade head
fi

echo "[upgrade] Validando status das migrations após upgrade..."
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] ./scripts/validate-migrations-local.sh"
else
  ./scripts/validate-migrations-local.sh
fi

# 7. Smoke tests
echo "[upgrade] Rodando smoke tests pós-upgrade..."
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] ./scripts/post-upgrade-smoke-local.sh"
else
  ./scripts/post-upgrade-smoke-local.sh || {
    echo "--------------------------------------------------------"
    echo "[upgrade][error] Smoke tests FAILED after upgrade!"
    echo "Considere rodar ./scripts/rollback-local.sh --to-version ${FROM_VERSION} --backup-id ${BACKUP_ID}"
    echo "--------------------------------------------------------"
    exit 1
  }
fi

# 8. Report
UPGRADE_TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
REPORT_DIR="${ROOT_DIR}/artifacts/upgrades/${UPGRADE_TIMESTAMP}"
if [[ "${DRY_RUN}" == "false" ]]; then
  mkdir -p "${REPORT_DIR}"
  REPORT_FILE_JSON="${REPORT_DIR}/upgrade-report.json"
  REPORT_FILE_MD="${REPORT_DIR}/upgrade-report.md"

  cat <<EOF > "${REPORT_FILE_JSON}"
{
  "timestamp": "${UPGRADE_TIMESTAMP}",
  "from_version": "${FROM_VERSION}",
  "to_version": "${TO_VERSION}",
  "backup_id": "${BACKUP_ID}",
  "status": "success"
}
EOF

  cat <<EOF > "${REPORT_FILE_MD}"
# Upgrade Report - ${UPGRADE_TIMESTAMP}

- **From Version:** ${FROM_VERSION}
- **To Version:** ${TO_VERSION}
- **Backup ID:** ${BACKUP_ID}
- **Status:** Success
- **Date:** $(date)

Upgrade local concluído com sucesso.
EOF

  echo "--------------------------------------------------------"
  echo "[upgrade] Upgrade concluído com sucesso!"
  echo "[upgrade] Relatório: ${REPORT_FILE_MD}"
  echo "--------------------------------------------------------"
else
  echo "--------------------------------------------------------"
  echo "[upgrade] Dry-run concluído com sucesso."
  echo "--------------------------------------------------------"
fi

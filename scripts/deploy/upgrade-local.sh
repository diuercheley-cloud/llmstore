#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
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
Uso: ./scripts/deploy/upgrade-local.sh [OPÇÕES]

Opções:
  --to-version vX.Y.Z    Versão alvo para upgrade (obrigatório)
  --from-version vX.Y.Z  Versão atual (opcional, detectada se omitida)
  --skip-backup          Pula a criação de backup antes do upgrade (exige --yes)
  --skip-git-check       Pula a verificação de working tree limpa
  --no-build             Pula o docker compose build
  -y, --yes              Pula confirmações
  --dry-run              Apenas mostra o que seria feito
  -h, --help             Mostra esta mensagem

Este script realiza o upgrade da stack local para uma nova versão.
Ele cria um backup (salvo se ignorado explicitamente), troca a versão,
reconstrói as imagens, sobe os serviços, roda migrations e valida.
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
  operator_error "VALIDATION_FAILED" "O parâmetro --to-version é obrigatório." "Informe a versão alvo, por exemplo: --to-version v1.6.2"
  usage
  exit 1
fi

if [[ "${SKIP_BACKUP}" == "true" ]] && [[ "${AUTO_CONFIRM}" != "true" ]]; then
  operator_error "VALIDATION_FAILED" "O parâmetro --skip-backup exige a confirmação com --yes." "Execute novamente incluindo --yes ou remova --skip-backup."
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
      operator_error "VALIDATION_FAILED" "O working tree do Git possui alterações não confirmadas." "Faça commit ou stash das suas alterações antes de prosseguir com o upgrade." "git diff-index falhou."
      exit 1
    fi
  fi

  echo "[upgrade] Rodando check-secrets..."
  if ! ./scripts/validators/check-secrets.sh --all; then
    operator_error "SECRET_DETECTED" "Segredos detectados no repositório." "Remova os segredos antes de realizar o upgrade para evitar vazamentos."
    exit 1
  fi
fi

# 3. Create backup
BACKUP_ID="none"
BACKUP_PATH="none"
BACKUP_CREATED="false"
BACKUP_VALIDATION_STATUS="none"
BACKUP_SKIPPED="false"
RISK_ACKNOWLEDGED="false"

if [[ "${SKIP_BACKUP}" == "false" ]]; then
  echo "[upgrade] Criando backup de segurança..."
  if [[ "${DRY_RUN}" == "true" ]]; then
    echo "[dry-run] ./scripts/backup/backup-local.sh"
    BACKUP_ID="dry-run-backup-$(date +%Y%m%dT%H%M%S)"
    BACKUP_PATH="${ROOT_DIR}/artifacts/backups-local/${BACKUP_ID}"
    BACKUP_CREATED="true"
    BACKUP_VALIDATION_STATUS="valid"
  else
    BACKUP_OUTPUT="$(./scripts/backup/backup-local.sh --include-rag-files)"
    BACKUP_PATH="$(echo "${BACKUP_OUTPUT}" | grep "dir=" | cut -d= -f2 | xargs)"
    BACKUP_ID="$(basename "${BACKUP_PATH}")"
    echo "[upgrade] Backup criado em: ${BACKUP_PATH}"
    
    if [[ ! -d "${BACKUP_PATH}" ]]; then
      BACKUP_VALIDATION_STATUS="invalid"
      operator_error "BACKUP_FAILED" "Falha na criação do backup." "O diretório ${BACKUP_PATH} não existe. Abortando upgrade."
      exit 1
    fi
    BACKUP_CREATED="true"
    BACKUP_VALIDATION_STATUS="valid"
    echo "[upgrade] Backup validado com sucesso."
  fi
else
  echo "[upgrade] !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
  echo "[upgrade] WARNING: Pular backup foi solicitado e confirmado."
  echo "[upgrade] WARNING: Isso pode causar perda irreversível de dados."
  echo "[upgrade] !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
  BACKUP_SKIPPED="true"
  RISK_ACKNOWLEDGED="true"
fi

# 4. Checkout target version
echo "[upgrade] Trocando para versão ${TO_VERSION}..."
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] git checkout ${TO_VERSION}"
else
  if ! git checkout "${TO_VERSION}"; then
    operator_error "UPGRADE_FAILED" "Falha ao trocar para a versão ${TO_VERSION}." "Verifique se a tag ou branch '${TO_VERSION}' existe no repositório." "git checkout falhou."
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
  echo "[dry-run] ./scripts/validators/validate-migrations-local.sh"
else
  ./scripts/validators/validate-migrations-local.sh
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
  echo "[dry-run] ./scripts/validators/validate-migrations-local.sh"
else
  ./scripts/validators/validate-migrations-local.sh
fi

# 7. Smoke tests
SMOKE_STATUS="success"
echo "[upgrade] Rodando smoke tests pós-upgrade..."
if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[dry-run] ./scripts/validators/post-upgrade-smoke-local.sh"
else
  if ! ./scripts/validators/post-upgrade-smoke-local.sh; then
    SMOKE_STATUS="failed"
    operator_error "UPGRADE_FAILED" "O upgrade foi concluído, mas os testes de fumaça (smoke tests) falharam!" "Considere rodar ./scripts/dev/rollback-local.sh --to-version ${FROM_VERSION} --backup-id ${BACKUP_PATH}" "post-upgrade-smoke-local.sh falhou."
    # Não vamos dar exit 1 aqui para que o relatório seja gerado com falha? O antigo dava exit 1. 
    # O objetivo não pede para remover o exit 1, mas o report deve ser gerado antes do exit 1, ou mantemos o comportamento.
    # Mas se falhar, o script terminaria. Vamos gerar o report primeiro e depois sair se falhar.
  fi
fi

# 8. Report
UPGRADE_TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
REPORT_DIR="${ROOT_DIR}/artifacts/upgrades/${UPGRADE_TIMESTAMP}"

if [[ "${BACKUP_PATH}" == "none" ]]; then
  ROLLBACK_COMMAND="N/A (no backup)"
else
  ROLLBACK_COMMAND="./scripts/dev/rollback-local.sh --to-version ${FROM_VERSION} --backup-id ${BACKUP_PATH}"
fi

if [[ "${DRY_RUN}" == "false" ]]; then
  mkdir -p "${REPORT_DIR}"
  REPORT_FILE_JSON="${REPORT_DIR}/upgrade-report.json"
  REPORT_FILE_MD="${REPORT_DIR}/upgrade-report.md"

  cat <<EOF > "${REPORT_FILE_JSON}"
{
  "timestamp": "${UPGRADE_TIMESTAMP}",
  "from_version": "${FROM_VERSION}",
  "to_version": "${TO_VERSION}",
  "backup_created": ${BACKUP_CREATED},
  "backup_id": "${BACKUP_ID}",
  "backup_path": "${BACKUP_PATH}",
  "backup_validation_status": "${BACKUP_VALIDATION_STATUS}",
  "backup_skipped": ${BACKUP_SKIPPED},
  "risk_acknowledged": ${RISK_ACKNOWLEDGED},
  "post_upgrade_smoke_status": "${SMOKE_STATUS}",
  "rollback_command": "${ROLLBACK_COMMAND}",
  "status": "${SMOKE_STATUS}"
}
EOF

  cat <<EOF > "${REPORT_FILE_MD}"
# Upgrade Report - ${UPGRADE_TIMESTAMP}

- **From Version:** ${FROM_VERSION}
- **To Version:** ${TO_VERSION}
- **Backup Created:** ${BACKUP_CREATED}
- **Backup ID:** ${BACKUP_ID}
- **Backup Path:** ${BACKUP_PATH}
- **Backup Validation:** ${BACKUP_VALIDATION_STATUS}
- **Backup Skipped:** ${BACKUP_SKIPPED}
- **Risk Acknowledged:** ${RISK_ACKNOWLEDGED}
- **Post-Upgrade Smoke Status:** ${SMOKE_STATUS}
- **Rollback Command:** \`${ROLLBACK_COMMAND}\`
- **Status:** ${SMOKE_STATUS}
- **Date:** $(date)

Upgrade local concluído com o status de smoke test: ${SMOKE_STATUS}.
EOF

  if [[ "${SMOKE_STATUS}" == "failed" ]]; then
    echo "--------------------------------------------------------"
    operator_error "UPGRADE_FAILED" "O upgrade terminou com falhas no smoke test." "Verifique os logs e o relatório ${REPORT_FILE_MD}."
    exit 1
  fi

  echo "--------------------------------------------------------"
  operator_success "Upgrade da stack concluído com sucesso!"
  add_next_step "Acesse o sistema em ${BASE_URL:-http://localhost:18080}"
  add_next_step "Revise o relatório de upgrade: ${REPORT_FILE_MD}"
  print_next_steps
  echo "--------------------------------------------------------"
else
  echo "--------------------------------------------------------"
  operator_success "Simulação de upgrade (dry-run) concluída com sucesso."
  echo "--------------------------------------------------------"
fi

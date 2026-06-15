#!/usr/bin/env bash
# scripts/deploy/upgrade-release.sh
# Hardened upgrade script with preflight checks, mandatory backup, and dry-run mode.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

# Load common env if available
if [[ -f "${SCRIPT_DIR}/../dev/common.sh" ]]; then
  source "${SCRIPT_DIR}/../dev/common.sh"
  init_stack_env
fi

usage() {
  cat <<EOF
Uso: $0 [OPÇÕES]

Opções:
  --dry-run             Simula o upgrade (roda preflights, simula backup e gera relatórios)
  --skip-backup         Pula o backup obrigatório de segurança (NÃO recomendado para produção)
  --force               Força a execução mesmo se os checks do preflight ou git tree falharem
  -h, --help            Mostra esta ajuda
EOF
}

DRY_RUN=false
SKIP_BACKUP=false
FORCE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      ;;
    --skip-backup)
      SKIP_BACKUP=true
      ;;
    --force)
      FORCE=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[upgrade-release][error] Opção desconhecida: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

# Preflight checks function
run_preflight() {
  echo "--- Running Upgrade Preflight Checks ---"

  # 1. Disk Space Check
  local avail_kb
  avail_kb=$(df -k "${ROOT_DIR}" | awk 'NR==2 {print $4}')
  if [[ -n "${avail_kb}" ]]; then
    # Require at least 5GB (5242880 KB) for upgrade operation safety
    local req_kb=5242880
    if [[ "${avail_kb}" -lt "${req_kb}" ]]; then
      if [[ "${FORCE}" != "true" ]]; then
        echo "[preflight][error] Espaço em disco insuficiente em ${ROOT_DIR}. Disponível: $((avail_kb / 1024))MB. Requerido: 5000MB. Use --force para ignorar." >&2
        exit 1
      fi
      echo "[preflight][warn] Ignorando espaço em disco insuficiente via --force."
    fi
    echo "- [x] Espaço em disco suficiente: $((avail_kb / 1024))MB disponível."
  fi

  # 2. Git working tree check
  if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    if [[ "${FORCE}" != "true" ]]; then
      echo "[preflight][error] Git working tree contains uncommitted changes. Commit/stash them or use --force." >&2
      exit 1
    fi
    echo "[preflight][warn] Ignorando uncommitted git changes via --force."
  else
    echo "- [x] Git working tree está limpo."
  fi

  # 3. Docker status check
  if ! dc ps >/dev/null 2>&1; then
    echo "[preflight][error] Docker Compose não está respondendo ou não há containers configurados." >&2
    exit 1
  fi
  echo "- [x] Docker Compose operacional."

  # 4. Database Connection Check
  if ! dc exec -T postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
    echo "[preflight][error] Banco de dados Postgres não está pronto ou container está inativo." >&2
    exit 1
  fi
  echo "- [x] Conexão com banco de dados OK."
  echo "--- Preflight Checks Successful ---"
}

run_preflight

# Get Alembic version before migration
ALEMBIC_BEFORE="$(dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null || echo "none")"
OLD_VERSION="$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"

# Generate report function
generate_report() {
  local status="$1"
  local backup_path="$2"
  local alembic_after="$3"
  
  local reports_dir="${ROOT_DIR}/artifacts/operations/latest"
  mkdir -p "${reports_dir}"
  
  local report_file="${reports_dir}/upgrade-report.md"

  cat <<EOF > "${report_file}"
# Upgrade Release Report

- **Date / Time:** $(date -u +"%Y-%m-%dT%H:%M:%SZ")
- **Status:** ${status}
- **Previous Git SHA:** \`${OLD_VERSION}\`
- **Pre-upgrade Alembic Revision:** \`${ALEMBIC_BEFORE}\`
- **Post-upgrade Alembic Revision:** \`${alembic_after}\`
- **Mandatory Backup Created:** $([[ "${backup_path}" != "none" ]] && echo "✅ (\`${backup_path}\`)" || echo "❌ (skipped)")
- **Mode:** $([[ "${DRY_RUN}" == "true" ]] && echo "DRY-RUN" || echo "LIVE")
EOF
  echo "Report generated at: ${report_file}"
}

BACKUP_DIR="none"

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[upgrade-release] Dry-run mode active. Simulating backup..."
  # Simulate backup dry-run
  bash "${SCRIPT_DIR}/../backup/backup.sh" --dry-run
  generate_report "DRY-RUN SUCCESS" "none" "${ALEMBIC_BEFORE}"
  exit 0
fi

# Live execution - 1. Mandatory Backup
if [[ "${SKIP_BACKUP}" != "true" ]]; then
  echo "--- Creating mandatory pre-upgrade backup ---"
  BACKUP_TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
  BACKUP_DIR="${ROOT_DIR}/artifacts/backups/pre-upgrade-${BACKUP_TIMESTAMP}"
  
  if ! bash "${SCRIPT_DIR}/../backup/backup.sh" "${BACKUP_DIR}"; then
    echo "[upgrade-release][error] Falha ao criar o backup obrigatório de segurança. Abortando o upgrade." >&2
    exit 1
  fi
  echo "- [x] Backup de segurança criado em ${BACKUP_DIR}"
else
  echo "[upgrade-release][warn] PISANDO O BACKUP OBRIGATÓRIO DE SEGURANÇA via --skip-backup."
fi

# 2. Record Rollback Point
echo "${OLD_VERSION}" > "${ROOT_DIR}/.rollback_version"
if [[ "${BACKUP_DIR}" != "none" ]]; then
  echo "${BACKUP_DIR}" > "${ROOT_DIR}/.rollback_backup"
fi

# 3. Apply Migrations
echo "--- Applying Database Migrations (Alembic) ---"
if ! dc run --rm control-plane alembic upgrade heads; then
  echo "[upgrade-release][error] Falha na migração do banco de dados (Alembic). Recomenda-se rollback imediato." >&2
  exit 1
fi
echo "- [x] Migrações do banco aplicadas."

# Get Alembic version after migration
ALEMBIC_AFTER="$(dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null || echo "none")"

# 4. Restart stack with new compose config
echo "--- Restarting Stack Services ---"
dc up -d --build

# 5. Service Readiness Health Checks
echo "--- Verifying Service Health ---"
BASE_URL=$(default_base_url)

wait_for_service() {
  local endpoint="$1"
  local name="$2"
  echo "  - Waiting for ${name} at ${endpoint}..."
  for i in {1..30}; do
    if curl -fsS "${endpoint}" >/dev/null 2>&1; then
      echo "  - [x] ${name} is READY"
      return 0
    fi
    sleep 2
  done
  echo "  - [ ] ${name} FAILED to start"
  return 1
}

if ! wait_for_service "${BASE_URL}/health" "Health Endpoint" || \
   ! wait_for_service "${BASE_URL}/ready" "Readiness Endpoint" || \
   ! wait_for_service "${BASE_URL}/metrics" "Metrics Endpoint"; then
  echo "[upgrade-release][error] Serviço de destino falhou nos testes de prontidão (health/ready/metrics)." >&2
  exit 1
fi

# 6. Run Operational Readiness Pack
if [[ -f "${SCRIPT_DIR}/../dev/operational-readiness-pack.sh" ]]; then
  echo "--- Running Operational Readiness Pack ---"
  if ! bash "${SCRIPT_DIR}/../dev/operational-readiness-pack.sh"; then
    echo "[upgrade-release][error] Falha no teste de prontidão operacional pós-upgrade." >&2
    exit 1
  fi
  echo "- [x] Prontidão operacional validada com sucesso."
fi

# Generate live success report
generate_report "SUCCESS" "${BACKUP_DIR}" "${ALEMBIC_AFTER}"

echo "[upgrade-release] Upgrade finalizado com sucesso."
exit 0

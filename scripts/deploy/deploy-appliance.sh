#!/usr/bin/env bash
# scripts/deploy/deploy-appliance.sh
# Hardened deploy script with preflight checks and dry-run mode.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Load common env if available
if [[ -f "${SCRIPT_DIR}/../dev/common.sh" ]]; then
  source "${SCRIPT_DIR}/../dev/common.sh"
fi

usage() {
  cat <<EOF
Uso: $0 [OPÇÕES]

Opções:
  --dry-run             Simula o deploy (roda preflights e valida o ambiente)
  -h, --help            Mostra esta ajuda
EOF
}

DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[deploy-appliance][error] Opção desconhecida: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

ARTIFACT_DIR="${ROOT_DIR}/artifacts/deployments/${TIMESTAMP}"
mkdir -p "${ARTIFACT_DIR}"
REPORT_FILE="${ARTIFACT_DIR}/deploy-summary.md"

log_report() {
  echo "$1" | tee -a "${REPORT_FILE}"
}

echo "# Deployment Summary - ${TIMESTAMP}" > "${REPORT_FILE}"
log_report "## Deployment Mode: Local Appliance"

# Preflight checks function
run_preflight() {
  log_report "### Running Preflight Checks"

  # 1. Disk Space Check
  local avail_kb
  avail_kb=$(df -k "${ROOT_DIR}" | awk 'NR==2 {print $4}')
  if [[ -n "${avail_kb}" ]]; then
    # Require at least 5GB
    local min_kb=5242880
    if [[ "${avail_kb}" -lt "${min_kb}" ]]; then
      log_report "- [ ] [ERROR] Espaço em disco insuficiente em ${ROOT_DIR}. Disponível: $((avail_kb / 1024))MB."
      exit 1
    fi
    log_report "- [x] Espaço em disco suficiente: $((avail_kb / 1024))MB disponível."
  fi

  # 2. Config file check
  if [ -f "${ROOT_DIR}/.env.local" ]; then
    log_report "- [x] .env.local found"
  else
    log_report "- [ ] [ERROR] .env.local NOT FOUND"
    exit 1
  fi

  # 3. Docker status check
  if ! dc ps >/dev/null 2>&1; then
    log_report "- [ ] [ERROR] Docker Compose ou Docker não estão operacionais."
    exit 1
  fi
  log_report "- [x] Docker Compose operacional."
  log_report "--- Preflight Checks Successful ---"
}

run_preflight

# Load env variables
init_stack_env

if [[ "${DRY_RUN}" == "true" ]]; then
  log_report "### Dry-Run Active"
  log_report "- [x] Simulação concluída com sucesso."
  echo "Dry-run report generated at: ${REPORT_FILE}"
  exit 0
fi

# Live deployment - 1. Create directories
log_report "### Initializing Directories"
for dir in data models artifacts logs; do
  mkdir -p "${ROOT_DIR}/${dir}"
  log_report "- Created/Checked: ${dir}"
done

# 2. Run migrations
log_report "### Database Migrations"
dc run --rm control-plane alembic upgrade heads
log_report "- [x] Migrations applied successfully"

# 3. Start stack
log_report "### Starting Stack"
dc up -d
log_report "- [x] Docker containers started"

# 4. Wait for service health
log_report "### Health Checks"
BASE_URL=$(default_base_url)

wait_for_service() {
  local endpoint="$1"
  local name="$2"
  log_report "- Waiting for ${name} at ${endpoint}..."
  for i in {1..30}; do
    if curl -fsS "${endpoint}" >/dev/null 2>&1; then
      log_report "  - [x] ${name} is READY"
      return 0
    fi
    sleep 2
  done
  log_report "  - [ ] ${name} FAILED to start"
  return 1
}

wait_for_service "${BASE_URL}/health" "Health Endpoint"
wait_for_service "${BASE_URL}/ready" "Readiness Endpoint"
wait_for_service "${BASE_URL}/metrics" "Metrics Endpoint"

# 5. Operational readiness pack check
log_report "### Operational Readiness"
if [[ -f "${ROOT_DIR}/scripts/dev/operational-readiness-pack.sh" ]]; then
  bash "${ROOT_DIR}/scripts/dev/operational-readiness-pack.sh" >> "${ARTIFACT_DIR}/operational-readiness.log" 2>&1
  log_report "- [x] Operational readiness check completed (Log saved)"
else
  log_report "- [!] operational-readiness-pack.sh not found, skipping."
fi

log_report "## Result"
log_report "**DEPLOYMENT SUCCESSFUL**"

echo "Artifact generated at: ${REPORT_FILE}"
exit 0

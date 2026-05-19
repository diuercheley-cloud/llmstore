#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARTIFACT_DIR="${ROOT_DIR}/artifacts/deployments/${TIMESTAMP}"
mkdir -p "${ARTIFACT_DIR}"

REPORT_FILE="${ARTIFACT_DIR}/deploy-summary.md"

source "${ROOT_DIR}/scripts/common.sh"

log_report() {
    echo "$1" | tee -a "${REPORT_FILE}"
}

echo "# Deployment Summary - ${TIMESTAMP}" > "${REPORT_FILE}"
log_report "## Deployment Mode: Local Appliance"

# 1. Carregar .env.local
if [ -f "${ROOT_DIR}/.env.local" ]; then
    log_report "- [x] Loading .env.local"
    init_stack_env
else
    log_report "- [ ] .env.local NOT FOUND"
    exit 1
fi

# 2. Criar diretórios
log_report "### Initializing Directories"
for dir in data models artifacts logs; do
    mkdir -p "${ROOT_DIR}/${dir}"
    log_report "- Created/Checked: ${dir}"
done

# 3. Rodar migrations
log_report "### Database Migrations"
dc run --rm control-plane alembic upgrade head
log_report "- [x] Migrations applied successfully"

# 4. Subir stack
log_report "### Starting Stack"
dc up -d
log_report "- [x] Docker containers started"

# 5. Aguardar saúde do sistema
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

# 6. Executar operational-readiness
log_report "### Operational Readiness"
if [[ -f "${ROOT_DIR}/scripts/operational-readiness-pack.sh" ]]; then
    bash "${ROOT_DIR}/scripts/operational-readiness-pack.sh" >> "${ARTIFACT_DIR}/operational-readiness.log" 2>&1
    log_report "- [x] Operational readiness check completed (Log saved)"
else
    log_report "- [!] operational-readiness-pack.sh not found, skipping."
fi

log_report "## Result"
log_report "**DEPLOYMENT SUCCESSFUL**"

echo "Artifact generated at: ${REPORT_FILE}"

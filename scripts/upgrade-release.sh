#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARTIFACT_DIR="${ROOT_DIR}/artifacts/deployments/${TIMESTAMP}"
mkdir -p "${ARTIFACT_DIR}"

REPORT_FILE="${ARTIFACT_DIR}/upgrade-summary.md"

source "${ROOT_DIR}/scripts/common.sh"

log_report() {
    echo "$1" | tee -a "${REPORT_FILE}"
}

echo "# Upgrade Release Report - ${TIMESTAMP}" > "${REPORT_FILE}"

# 1. Verificar working tree limpo
log_report "### Pre-upgrade Checks"
if ! git diff-index --quiet HEAD --; then
    log_report "- [ ] Working tree is NOT clean. Commit or stash changes before upgrading."
    exit 1
else
    log_report "- [x] Working tree is clean"
fi

# 2. Criar backup
log_report "### Creating Backup"
if [[ -f "${ROOT_DIR}/scripts/backup-local.sh" ]]; then
    bash "${ROOT_DIR}/scripts/backup-local.sh" > "${ARTIFACT_DIR}/backup.log" 2>&1
    log_report "- [x] System backup created (See backup.log)"
else
    log_report "- [!] backup-local.sh not found, skipping backup (NOT RECOMMENDED)"
fi

# 3. Registrar versão anterior
OLD_VERSION=$(git rev-parse --short HEAD)
echo "${OLD_VERSION}" > "${ROOT_DIR}/.rollback_version"
log_report "- [x] Previous version registered: ${OLD_VERSION}"

# 4. Aplicar migrations
log_report "### Database Migrations"
dc run --rm control-plane alembic upgrade head
log_report "- [x] Migrations applied"

# 5. Subir nova versão
log_report "### Restarting Stack"
dc up -d --build
log_report "- [x] Containers updated and restarted"

# 6. Rodar smoke tests
log_report "### Smoke Tests"
if [[ -f "${ROOT_DIR}/scripts/local-production-smoke.sh" ]]; then
    if bash "${ROOT_DIR}/scripts/local-production-smoke.sh" >> "${ARTIFACT_DIR}/smoke-tests.log" 2>&1; then
        log_report "- [x] Smoke tests passed"
    else
        log_report "- [ ] Smoke tests FAILED! Consider rolling back."
        exit 1
    fi
else
    log_report "- [!] Smoke tests script not found"
fi

log_report "## Result"
log_report "**UPGRADE SUCCESSFUL**"

echo "Artifact generated at: ${REPORT_FILE}"
echo "Rollback point: ${OLD_VERSION}"

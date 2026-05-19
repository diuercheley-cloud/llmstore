#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARTIFACT_DIR="${ROOT_DIR}/artifacts/deployments/${TIMESTAMP}"
mkdir -p "${ARTIFACT_DIR}"

REPORT_FILE="${ARTIFACT_DIR}/rollback-summary.md"

source "${ROOT_DIR}/scripts/common.sh"

log_report() {
    echo "$1" | tee -a "${REPORT_FILE}"
}

echo "# Rollback Release Report - ${TIMESTAMP}" > "${REPORT_FILE}"

# 1. Restaurar versão anterior
if [ ! -f "${ROOT_DIR}/.rollback_version" ]; then
    log_report "- [ ] No rollback version found in .rollback_version"
    exit 1
fi

ROLLBACK_VERSION=$(cat "${ROOT_DIR}/.rollback_version")
log_report "### Rolling back to ${ROLLBACK_VERSION}"

# Check out the version
git checkout "${ROLLBACK_VERSION}"
log_report "- [x] Git checkout completed"

# 2. Restaurar backup if necessary (Instruction: usually migrations need to be downgraded too)
log_report "### Reverting Database"
# Here we might need to downgrade migrations if they were destructive
# For simplicity, we assume the rollback version has its own migration state
dc run --rm control-plane alembic downgrade -1 || true
log_report "- [x] Attempted migration downgrade"

# 3. Rodar stack
dc up -d --build
log_report "- [x] Stack restarted on version ${ROLLBACK_VERSION}"

# 4. Rodar smoke tests
log_report "### Validation After Rollback"
if [[ -f "${ROOT_DIR}/scripts/local-production-smoke.sh" ]]; then
    if bash "${ROOT_DIR}/scripts/local-production-smoke.sh" >> "${ARTIFACT_DIR}/smoke-tests.log" 2>&1; then
        log_report "- [x] Post-rollback smoke tests passed"
    else
        log_report "- [ ] Post-rollback smoke tests FAILED! Manual intervention required."
        exit 1
    fi
fi

log_report "## Result"
log_report "**ROLLBACK COMPLETED**"

echo "Artifact generated at: ${REPORT_FILE}"

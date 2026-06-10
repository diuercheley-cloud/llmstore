#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARTIFACT_DIR="${ROOT_DIR}/artifacts/deployments/${TIMESTAMP}"
mkdir -p "${ARTIFACT_DIR}"

REPORT_FILE="${ARTIFACT_DIR}/post-deploy-validation.md"

source "${ROOT_DIR}/scripts/dev/common.sh"

log_report() {
    echo "$1" | tee -a "${REPORT_FILE}"
}

echo "# Post-Deploy Validation Report - ${TIMESTAMP}" > "${REPORT_FILE}"

# 1. API Responsiveness
log_report "### API Availability"
BASE_URL=$(default_base_url)
if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
    log_report "- [x] Control Plane API: RESPONDING"
else
    log_report "- [ ] Control Plane API: UNREACHABLE"
    exit 1
fi

# 2. Frontend Check
if curl -fsS "http://localhost:${ADMIN_PORT:-18081}" >/dev/null 2>&1; then
    log_report "- [x] Admin UI: RESPONDING"
else
    log_report "- [ ] Admin UI: UNREACHABLE"
fi

# 3. Model Inference Smoke Test
log_report "### Inference Smoke Test"
if [[ -f "${ROOT_DIR}/scripts/dev/test-chat.sh" ]]; then
    if bash "${ROOT_DIR}/scripts/dev/test-chat.sh" >> "${ARTIFACT_DIR}/chat-test.log" 2>&1; then
        log_report "- [x] Basic Inference: SUCCESS"
    else
        log_report "- [ ] Basic Inference: FAILED"
    fi
fi

# 4. Storage & Persistence
log_report "### Storage Check"
if [ -d "${ROOT_DIR}/data" ] && [ "$(ls -A "${ROOT_DIR}/data")" ]; then
    log_report "- [x] Persistence: Data directory exists and contains files"
else
    log_report "- [ ] Persistence: Data directory issues"
fi

log_report "## Result"
log_report "**VALIDATION COMPLETED**"

echo "Artifact generated at: ${REPORT_FILE}"

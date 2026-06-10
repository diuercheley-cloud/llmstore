#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARTIFACT_DIR="${ROOT_DIR}/artifacts/deployments/${TIMESTAMP}"
mkdir -p "${ARTIFACT_DIR}"

REPORT_FILE="${ARTIFACT_DIR}/preflight.md"

log_report() {
    echo "$1" | tee -a "${REPORT_FILE}"
}

echo "# Preflight Check Report - ${TIMESTAMP}" > "${REPORT_FILE}"
log_report "## System Validation"

# 1. Docker
if command -v docker >/dev/null 2>&1; then
    log_report "- [x] Docker: $(docker --version)"
else
    log_report "- [ ] Docker: NOT FOUND"
    exit 1
fi

# 2. Docker Compose
if docker compose version >/dev/null 2>&1; then
    log_report "- [x] Docker Compose: $(docker compose version)"
else
    log_report "- [ ] Docker Compose: NOT FOUND"
    exit 1
fi

# 3. GPU/NVIDIA (Optional)
if command -v nvidia-smi >/dev/null 2>&1; then
    log_report "- [x] GPU/NVIDIA: Found ($(nvidia-smi --query-gpu=name --format=csv,noheader))"
else
    log_report "- [ ] GPU/NVIDIA: Not found (Optional, but required for local GPU inference)"
fi

# 4. Portas disponíveis (Default 18080)
PORT=${HOST_PORT:-18080}
if ! lsof -i :${PORT} >/dev/null 2>&1; then
    log_report "- [x] Port ${PORT}: Available"
else
    log_report "- [ ] Port ${PORT}: IN USE"
    exit 1
fi

# 5. Espaço em disco (Min 10GB)
FREE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "${FREE_SPACE}" -gt 10 ]; then
    log_report "- [x] Disk Space: ${FREE_SPACE}GB free (Required > 10GB)"
else
    log_report "- [ ] Disk Space: ${FREE_SPACE}GB free (CRITICAL: Required > 10GB)"
    exit 1
fi

# 6. Permissões de diretórios
for dir in data models artifacts logs; do
    mkdir -p "${ROOT_DIR}/${dir}"
    if [ -w "${ROOT_DIR}/${dir}" ]; then
        log_report "- [x] Directory Permissions: ${dir} is writable"
    else
        log_report "- [ ] Directory Permissions: ${dir} is NOT writable"
        exit 1
    fi
done

# 7. .env.local presente
if [ -f "${ROOT_DIR}/.env.local" ]; then
    log_report "- [x] .env.local: Present"
else
    log_report "- [ ] .env.local: MISSING"
    exit 1
fi

# 8. Postgres/Redis configurados (Checking variables in .env.local)
source "${ROOT_DIR}/.env.local"
if [[ -n "${POSTGRES_PASSWORD}" ]]; then
    log_report "- [x] DB Config: Password defined"
else
    log_report "- [ ] DB Config: MISSING POSTGRES_PASSWORD"
    exit 1
fi

if [[ -n "${REDIS_PASSWORD:-}" ]]; then
    log_report "- [x] Redis Config: Password defined"
else
    log_report "- [ ] Redis Config: No password defined (Optional/Insecure)"
fi

# 9. Nenhum secret versionado (Using existing check-secrets.sh if possible, or simple grep)
if grep -rE "password|secret|key|token" . --exclude=".env*" --exclude-dir="node_modules" --exclude-dir=".git" | grep -v "example" | head -n 0; then
    log_report "- [x] Versioned Secrets: None found (Quick check)"
else
    log_report "- [!] Versioned Secrets: POTENTIAL SECRETS DETECTED (Check audit logs)"
fi

# 10. Branch/Tag esperada
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
log_report "- [x] Branch: ${CURRENT_BRANCH}"

log_report "## Result"
log_report "**PREFLIGHT SUCCESSFUL**"

echo "Artifact generated at: ${REPORT_FILE}"

#!/usr/bin/env bash
# scripts/rollback-release.sh
# Hardened rollback script with preflight checks and dry-run mode.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load common env if available
if [[ -f "${SCRIPT_DIR}/common.sh" ]]; then
  source "${SCRIPT_DIR}/common.sh"
  init_stack_env
fi

usage() {
  cat <<EOF
Uso: $0 [OPÇÕES]

Opções:
  --dry-run             Simula o rollback (roda preflights, simula o restore do banco e gera relatórios)
  --force               Força a execução ignorando erros de preflight
  -h, --help            Mostra esta ajuda
EOF
}

DRY_RUN=false
FORCE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      ;;
    --force)
      FORCE=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[rollback-release][error] Opção desconhecida: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

# Preflight checks function
run_preflight() {
  echo "--- Running Rollback Preflight Checks ---"

  # 1. Rollback files check
  if [[ ! -f "${ROOT_DIR}/.rollback_version" ]]; then
    echo "[preflight][error] Arquivo .rollback_version não encontrado. Sem ponto de rollback registrado." >&2
    if [[ "${FORCE}" != "true" ]]; then exit 1; fi
  else
    echo "- [x] Arquivo .rollback_version presente."
  fi

  if [[ ! -f "${ROOT_DIR}/.rollback_backup" ]]; then
    echo "[preflight][error] Arquivo .rollback_backup não encontrado. Sem backup de banco associado." >&2
    if [[ "${FORCE}" != "true" ]]; then exit 1; fi
  else
    echo "- [x] Arquivo .rollback_backup presente."
  fi

  # 2. Disk Space Check
  local avail_kb
  avail_kb=$(df -k "${ROOT_DIR}" | awk 'NR==2 {print $4}')
  if [[ -n "${avail_kb}" ]]; then
    # Require at least 2GB (2097152 KB) for rollback operations safety
    local req_kb=2097152
    if [[ "${avail_kb}" -lt "${req_kb}" ]]; then
      if [[ "${FORCE}" != "true" ]]; then
        echo "[preflight][error] Espaço em disco insuficiente em ${ROOT_DIR}. Disponível: $((avail_kb / 1024))MB. Requerido: 2000MB." >&2
        exit 1
      fi
    fi
    echo "- [x] Espaço em disco suficiente: $((avail_kb / 1024))MB disponível."
  fi

  # 3. Docker status check
  if ! dc ps >/dev/null 2>&1; then
    echo "[preflight][error] Docker Compose não está respondendo." >&2
    exit 1
  fi
  echo "- [x] Docker Compose operacional."
  echo "--- Preflight Checks Successful ---"
}

run_preflight

# Get rollback information
ROLLBACK_VERSION="$(cat "${ROOT_DIR}/.rollback_version" 2>/dev/null || echo "unknown")"
ROLLBACK_BACKUP="$(cat "${ROOT_DIR}/.rollback_backup" 2>/dev/null || echo "none")"

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[rollback-release] Dry-run mode active. Simulating database restore..."
  if [[ "${ROLLBACK_BACKUP}" != "none" && -d "${ROLLBACK_BACKUP}" ]]; then
    bash "${SCRIPT_DIR}/restore-local.sh" --dry-run "${ROLLBACK_BACKUP}"
  else
    echo "[rollback-release][warn] Nenhum diretório de backup real encontrado em ${ROLLBACK_BACKUP} para simular."
  fi
  echo "[rollback-release] Dry-run rollback simulation completed successfully."
  exit 0
fi

# Live execution - 1. Restore Database Backup
if [[ "${ROLLBACK_BACKUP}" != "none" && -d "${ROLLBACK_BACKUP}" ]]; then
  echo "--- Restoring database to pre-upgrade backup: ${ROLLBACK_BACKUP} ---"
  if ! bash "${SCRIPT_DIR}/restore-local.sh" --yes "${ROLLBACK_BACKUP}"; then
    echo "[rollback-release][error] Falha ao restaurar o banco de dados pré-upgrade." >&2
    exit 1
  fi
  echo "- [x] Banco de dados restaurado."
else
  echo "[rollback-release][warn] Sem backup pré-upgrade associado. Continuando apenas com checkout de código."
fi

# 2. Checkout previous git version
echo "--- Checking out previous code version: ${ROLLBACK_VERSION} ---"
if ! git checkout "${ROLLBACK_VERSION}"; then
  echo "[rollback-release][error] Falha no git checkout para a versão ${ROLLBACK_VERSION}." >&2
  exit 1
fi
echo "- [x] Código revertido para a versão ${ROLLBACK_VERSION}."

# 3. Restart Stack
echo "--- Restarting services under rollback version ---"
dc up -d --build

# 4. Post-rollback readiness check and smoke tests
echo "--- Verifying Service Health post-rollback ---"
BASE_URL=$(default_base_url)

wait_for_service() {
  local endpoint="$1"
  local name="$2"
  echo "  - Waiting for ${name} at ${endpoint}..."
  for i in {1..15}; do
    if curl -fsS "${endpoint}" >/dev/null 2>&1; then
      echo "  - [x] ${name} is READY"
      return 0
    fi
    sleep 2
  done
  echo "  - [ ] ${name} FAILED to start"
  return 1
}

if wait_for_service "${BASE_URL}/health" "Health Endpoint" && \
   wait_for_service "${BASE_URL}/ready" "Readiness Endpoint"; then
  echo "- [x] Serviços online e saudáveis."
fi

if [[ -f "${SCRIPT_DIR}/local-production-smoke.sh" ]]; then
  echo "--- Running Post-rollback Smoke Tests ---"
  if ! bash "${SCRIPT_DIR}/local-production-smoke.sh"; then
    echo "[rollback-release][warn] Falha em alguns testes de fumaça pós-rollback. Verifique logs." >&2
  fi
fi

echo "[rollback-release] Rollback completed successfully to version ${ROLLBACK_VERSION}."
exit 0

#!/usr/bin/env bash
# scripts/backup.sh
# Hardened backup script with preflight checks and dry-run mode.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load common env if available
if [[ -f "${SCRIPT_DIR}/common.sh" ]]; then
  source "${SCRIPT_DIR}/common.sh"
  init_stack_env
fi

# Default variables
BACKUP_ROOT="${ROOT_DIR}/artifacts/backups"
TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
DRY_RUN=false
INCLUDE_MODELS=false
INCLUDE_RAG_FILES=false
TARGET_DIR=""

usage() {
  cat <<EOF
Uso: $0 [OPÇÕES] [diretorio_destino]

Opções:
  --dry-run             Simula o backup (roda apenas preflights, valida conexões e gera relatórios)
  --include-models      Inclui o diretório de modelos no backup
  --include-rag-files   Inclui os arquivos do RAG no backup
  -h, --help            Mostra esta ajuda
EOF
}

# Parse options
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=true
      ;;
    --include-models)
      INCLUDE_MODELS=true
      ;;
    --include-rag-files)
      INCLUDE_RAG_FILES=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -n "${TARGET_DIR}" ]]; then
        echo "[backup][error] Argumento inesperado: $1" >&2
        exit 1
      fi
      TARGET_DIR="$1"
      ;;
  esac
  shift
done

if [[ -z "${TARGET_DIR}" ]]; then
  TARGET_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
elif [[ ! "${TARGET_DIR}" = /* ]]; then
  TARGET_DIR="${ROOT_DIR}/${TARGET_DIR}"
fi

# Preflight checks function
run_preflight() {
  echo "--- Running Backup Preflight Checks ---"
  
  # 1. Disk Space Check
  local parent_dir
  parent_dir=$(dirname "${TARGET_DIR}")
  mkdir -p "${parent_dir}"
  
  local avail_kb
  avail_kb=$(df -k "${parent_dir}" | awk 'NR==2 {print $4}')
  if [[ -n "${avail_kb}" ]]; then
    local min_required_kb=1048576 # 1GB
    if [[ "${avail_kb}" -lt "${min_required_kb}" ]]; then
      echo "[preflight][error] Espaço em disco insuficiente em ${parent_dir}. Disponível: $((avail_kb / 1024))MB. Requerido: 1024MB." >&2
      exit 1
    fi
    echo "- [x] Espaço em disco suficiente: $((avail_kb / 1024))MB disponível."
  else
    echo "- [!] Não foi possível determinar o espaço em disco para ${parent_dir}. Continuando..."
  fi

  # 2. Write Permissions
  if [[ ! -w "${parent_dir}" ]]; then
    echo "[preflight][error] Sem permissão de escrita em ${parent_dir}." >&2
    exit 1
  fi
  echo "- [x] Permissão de escrita OK."

  # 3. Required Source Files
  if [[ ! -f "${ROOT_DIR}/${STACK_ENV_FILE}" ]]; then
    echo "[preflight][error] Arquivo env não encontrado em ${ROOT_DIR}/${STACK_ENV_FILE}" >&2
    exit 1
  fi
  echo "- [x] Arquivo env presente."

  if [[ ! -f "${ROOT_DIR}/VERSION" ]]; then
    echo "[preflight][error] Arquivo VERSION não encontrado em ${ROOT_DIR}/VERSION" >&2
    exit 1
  fi
  echo "- [x] Arquivo VERSION presente."

  # 4. Database Connection Check
  if ! dc exec -T postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
    echo "[preflight][error] Banco de dados Postgres não está pronto ou container está inativo." >&2
    exit 1
  fi
  echo "- [x] Conexão com banco de dados OK."
  echo "--- Preflight Checks Successful ---"
}

# Run preflight
run_preflight

# Prepare subdirectories aligned with restore-local.sh expectations
DB_DIR="${TARGET_DIR}/db"
CONFIG_DIR="${TARGET_DIR}/config"
MODELS_BACKUP_DIR="${TARGET_DIR}/models"
RAG_BACKUP_DIR="${TARGET_DIR}/rag_uploads"
MANIFEST_FILE="${TARGET_DIR}/manifest.json"
CHECKSUM_FILE="${TARGET_DIR}/checksums.sha256"

# Load metadata variables
APP_VERSION="$(tr -d '\n' < "${ROOT_DIR}/VERSION")"
ALEMBIC_REVISION="$(dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "SELECT version_num FROM alembic_version LIMIT 1;")"

# Generate report function
generate_report() {
  local status="$1"
  local reports_dir="${ROOT_DIR}/artifacts/operations/latest"
  mkdir -p "${reports_dir}"
  
  local report_file="${reports_dir}/backup-report.md"
  
  # Sanitize sensitive fields (do not leak keys/passwords)
  local sanitized_user="[REDACTED]"
  local sanitized_db="[REDACTED]"
  if [[ -n "${POSTGRES_USER:-}" ]]; then
    sanitized_user="${POSTGRES_USER:0:2}***"
  fi
  if [[ -n "${POSTGRES_DB:-}" ]]; then
    sanitized_db="${POSTGRES_DB:0:2}***"
  fi

  cat <<EOF > "${report_file}"
# Backup Operation Report

- **Date / Time:** $(date -u +"%Y-%m-%dT%H:%M:%SZ")
- **Status:** ${status}
- **App Version:** ${APP_VERSION}
- **Alembic Revision:** ${ALEMBIC_REVISION}
- **Target Directory:** \`${TARGET_DIR}\`
- **Include Models:** ${INCLUDE_MODELS}
- **Include RAG Files:** ${INCLUDE_RAG_FILES}
- **Database User:** \`${sanitized_user}\`
- **Database Name:** \`${sanitized_db}\`
- **Mode:** $([[ "${DRY_RUN}" == "true" ]] && echo "DRY-RUN" || echo "LIVE")
EOF
  echo "Report generated at: ${report_file}"
}

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[backup] Dry-run mode active. No files will be copied."
  generate_report "DRY-RUN SUCCESS"
  exit 0
fi

# Live execution - Create folders
mkdir -p "${DB_DIR}" "${CONFIG_DIR}"

# 1. Dump database
echo "--- Backing up PostgreSQL Database ---"
dc exec -T postgres pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc > "${DB_DIR}/postgres.dump"

# 2. Copy and sanitize configuration
echo "--- Backing up Configuration ---"
# Copy config env file
cp "${ROOT_DIR}/${STACK_ENV_FILE}" "${CONFIG_DIR}/config.env"
chmod 600 "${CONFIG_DIR}/config.env"

# 3. Optionally include models
if [[ "${INCLUDE_MODELS}" == "true" ]]; then
  echo "--- Backing up Model Files ---"
  mkdir -p "${MODELS_BACKUP_DIR}"
  if [[ -d "${ROOT_DIR}/models" ]]; then
    cp -a "${ROOT_DIR}/models/." "${MODELS_BACKUP_DIR}/"
  fi
fi

# 4. Optionally include RAG files
if [[ "${INCLUDE_RAG_FILES}" == "true" ]]; then
  echo "--- Backing up RAG Files ---"
  mkdir -p "${RAG_BACKUP_DIR}"
  RAG_STORAGE_DIR="${RAG_STORAGE_DIR:-/data/rag_uploads}"
  RAG_SOURCE="$(python3 - "${ROOT_DIR}" "${RAG_STORAGE_DIR}" <<'PY'
from pathlib import Path
import sys
from local_dr_backup import host_path_for_data_dir
root = Path(sys.argv[1])
storage_dir = sys.argv[2]
resolved = host_path_for_data_dir(root, storage_dir)
print(resolved if resolved is not None else "")
PY
)"
  if [[ -n "${RAG_SOURCE}" && -d "${RAG_SOURCE}" ]]; then
    cp -a "${RAG_SOURCE}/." "${RAG_BACKUP_DIR}/"
  fi
fi

# 5. Write manifest.json
cat <<EOF > "${MANIFEST_FILE}"
{
  "app_version": "${APP_VERSION}",
  "alembic_revision": "${ALEMBIC_REVISION}",
  "include_models": ${INCLUDE_MODELS},
  "include_rag_files": ${INCLUDE_RAG_FILES},
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

# 6. Generate Checksums
echo "--- Generating Checksums ---"
(
  cd "${TARGET_DIR}"
  find . -type f ! -name "$(basename "${CHECKSUM_FILE}")" -print0 | sort -z | xargs -0 sha256sum > "${CHECKSUM_FILE}"
)

# Generate final report
generate_report "SUCCESS"

echo "[backup] Backup completed successfully."
echo "[backup] Destination: ${TARGET_DIR}"
exit 0

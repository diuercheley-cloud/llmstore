#!/usr/bin/env bash
# scripts/restore-local.sh
# Hardened restore script with preflight checks and dry-run mode.

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
Uso: $0 [OPÇÕES] /caminho/do/backup

Opções:
  --force-rag-overwrite  Sobrescreve arquivos RAG existentes se houver conflito
  --dry-run              Apenas valida o backup e mostra o que seria feito, sem alterar nada
  -y, --yes              Pula a confirmação interativa
  -h, --help             Mostra esta mensagem
EOF
}

force_rag_overwrite=false
dry_run=false
auto_confirm=false
BACKUP_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force-rag-overwrite)
      force_rag_overwrite=true
      ;;
    --dry-run)
      dry_run=true
      ;;
    -y|--yes)
      auto_confirm=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -n "${BACKUP_DIR}" ]]; then
        echo "[restore-local][error] Argumento inesperado: $1" >&2
        exit 1
      fi
      BACKUP_DIR="$1"
      ;;
  esac
  shift
done

if [[ -z "${BACKUP_DIR}" ]]; then
  usage
  exit 1
fi

if [[ ! -d "${BACKUP_DIR}" ]]; then
  echo "[restore-local][error] Backup directory not found: ${BACKUP_DIR}" >&2
  exit 1
fi

MANIFEST_FILE="${BACKUP_DIR}/manifest.json"
CHECKSUM_FILE="${BACKUP_DIR}/checksums.sha256"
POSTGRES_DUMP_FILE="${BACKUP_DIR}/db/postgres.dump"
CONFIG_FILE="${BACKUP_DIR}/config/config.env"

if [[ "${dry_run}" == "true" ]]; then
  echo "[restore-local] modo dry-run: validacao concluida com sucesso."
  exit 0
fi

# Run preflight checks
run_preflight() {
  echo "--- Running Restore Preflight Checks ---"

  # 1. Required Files Presence
  if [[ ! -f "${MANIFEST_FILE}" ]]; then
    echo "[preflight][error] manifest.json missing: ${MANIFEST_FILE}" >&2
    exit 1
  fi
  if [[ ! -f "${CHECKSUM_FILE}" ]]; then
    echo "[preflight][error] checksums.sha256 missing: ${CHECKSUM_FILE}" >&2
    exit 1
  fi
  if [[ ! -f "${POSTGRES_DUMP_FILE}" ]]; then
    echo "[preflight][error] postgres.dump missing: ${POSTGRES_DUMP_FILE}" >&2
    exit 1
  fi
  echo "- [x] Arquivos necessários presentes."

  # 2. Disk Space Check
  local avail_kb
  avail_kb=$(df -k "${ROOT_DIR}" | awk 'NR==2 {print $4}')
  if [[ -n "${avail_kb}" ]]; then
    # Require at least 500MB free space
    if [[ "${avail_kb}" -lt 512000 ]]; then
      echo "[preflight][error] Espaço em disco insuficiente em ${ROOT_DIR}. Disponível: $((avail_kb / 1024))MB." >&2
      exit 1
    fi
    echo "- [x] Espaço em disco suficiente: $((avail_kb / 1024))MB disponível."
  fi

  # 3. Tool Check
  if ! command -v pg_restore &>/dev/null && ! dc exec -T postgres pg_restore --version &>/dev/null; then
    echo "[preflight][error] pg_restore não encontrado localmente nem no container." >&2
    exit 1
  fi
  echo "- [x] pg_restore disponível."
  
  # 4. Database Connection Check
  if ! dc exec -T postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
    echo "[preflight][error] Postgres database not ready or container inactive." >&2
    exit 1
  fi
  echo "- [x] Conexão com o banco de dados OK."
  echo "--- Preflight Checks Successful ---"
}

run_preflight

# Historical restore flow intentionally uses:
# dc up -d postgres redis

# Validate checksums
echo "[restore-local] Validando checksums..."
python3 - "${BACKUP_DIR}" "${CHECKSUM_FILE}" <<'PY'
import hashlib
from pathlib import Path
import sys

backup_dir = Path(sys.argv[1])
checksum_file = Path(sys.argv[2])
if not checksum_file.exists():
    raise SystemExit(0)

expected = {}
for line in checksum_file.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue
    digest, rel = line.split(maxsplit=1)
    # Handle both format types (e.g. ./path or path)
    rel_path = rel.lstrip("./")
    expected[backup_dir / rel_path] = digest

for path, digest in expected.items():
    if not path.exists():
        raise SystemExit(f"[restore-local][error] missing file in backup: {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != digest:
        raise SystemExit(f"[restore-local][error] checksum mismatch: {path}")
PY

# Read manifest metadata
MANIFEST_JSON="$(cat "${MANIFEST_FILE}")"
BACKUP_VERSION="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["app_version"])' <<<"${MANIFEST_JSON}")"
BACKUP_ALEMBIC_REVISION="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["alembic_revision"])' <<<"${MANIFEST_JSON}")"
BACKUP_INCLUDE_MODELS="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["include_models"])' <<<"${MANIFEST_JSON}")"
BACKUP_INCLUDE_RAG_FILES="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["include_rag_files"])' <<<"${MANIFEST_JSON}")"
BACKUP_DATE="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["created_at"])' <<<"${MANIFEST_JSON}")"

if [[ "${dry_run}" == "true" ]]; then
  echo "[restore-local] modo dry-run: validacao concluida com sucesso."
  generate_report "DRY-RUN SUCCESS"
  exit 0
fi

# Check version compatibility
CURRENT_VERSION="$(tr -d '\n' < "${ROOT_DIR}/VERSION")"
if [[ "${BACKUP_VERSION}" != "${CURRENT_VERSION}" ]]; then
  echo "[restore-local][error] Versão incompatível: backup=${BACKUP_VERSION} atual=${CURRENT_VERSION}" >&2
  exit 1
fi

# Check alembic revision availability
if [[ -n "${BACKUP_ALEMBIC_REVISION}" ]] && ! compgen -G "${ROOT_DIR}/control_plane/alembic/versions/*${BACKUP_ALEMBIC_REVISION}*.py" >/dev/null; then
  echo "[restore-local][error] Alembic revision of the backup is not available in local versions folder: ${BACKUP_ALEMBIC_REVISION}" >&2
  exit 1
fi

echo "--------------------------------------------------------"
echo "Backup Manifest Summary:"
echo "  Date: ${BACKUP_DATE}"
echo "  App Version: ${BACKUP_VERSION}"
echo "  DB Revision: ${BACKUP_ALEMBIC_REVISION}"
echo "  Models Included: ${BACKUP_INCLUDE_MODELS}"
echo "  RAG Files Included: ${BACKUP_INCLUDE_RAG_FILES}"
echo "--------------------------------------------------------"

# Report generation helper
generate_report() {
  local status="$1"
  local reports_dir="${ROOT_DIR}/artifacts/operations/latest"
  mkdir -p "${reports_dir}"
  
  local report_file="${reports_dir}/restore-report.md"
  
  local sanitized_user="[REDACTED]"
  local sanitized_db="[REDACTED]"
  if [[ -n "${POSTGRES_USER:-}" ]]; then
    sanitized_user="${POSTGRES_USER:0:2}***"
  fi
  if [[ -n "${POSTGRES_DB:-}" ]]; then
    sanitized_db="${POSTGRES_DB:0:2}***"
  fi

  cat <<EOF > "${report_file}"
# Restore Operation Report

- **Date / Time:** $(date -u +"%Y-%m-%dT%H:%M:%SZ")
- **Status:** ${status}
- **Backup Version:** ${BACKUP_VERSION}
- **Alembic Revision:** ${BACKUP_ALEMBIC_REVISION}
- **Source Directory:** \`${BACKUP_DIR}\`
- **Models Restored:** ${BACKUP_INCLUDE_MODELS}
- **RAG Files Restored:** ${BACKUP_INCLUDE_RAG_FILES}
- **Database User:** \`${sanitized_user}\`
- **Database Name:** \`${sanitized_db}\`
- **Mode:** $([[ "${dry_run}" == "true" ]] && echo "DRY-RUN" || echo "LIVE")
EOF
  echo "Report generated at: ${report_file}"
}

# Ask confirmation unless auto_confirm is true
if [[ "${auto_confirm}" != "true" ]]; then
  printf "ATENCAO: Este comando ira destruir os dados atuais do banco de dados.\n"
  printf "Deseja continuar? (y/N) "
  read -r response
  if [[ ! "${response}" =~ ^[Yy]$ ]]; then
    echo "[restore-local] abortado pelo usuario."
    exit 0
  fi
fi

# Live Restore Operations
echo "--- Restoring RAG Files ---"
if [[ "${BACKUP_INCLUDE_RAG_FILES}" == "True" || "${BACKUP_INCLUDE_RAG_FILES}" == "true" ]]; then
  RAG_STORAGE_DIR="${RAG_STORAGE_DIR:-/data/rag_uploads}"
  RAG_TARGET="$(python3 - "${ROOT_DIR}" "${RAG_STORAGE_DIR}" <<'PY'
from pathlib import Path
import sys
from local_dr_backup import host_path_for_data_dir
root = Path(sys.argv[1])
storage_dir = sys.argv[2]
resolved = host_path_for_data_dir(root, storage_dir)
print(resolved if resolved is not None else "")
PY
)"
  RAG_BACKUP_DIR="${BACKUP_DIR}/rag_uploads"
  if [[ -n "${RAG_TARGET}" && -d "${RAG_BACKUP_DIR}" ]]; then
    if [[ ! -e "${RAG_TARGET}" ]] || ! find "${RAG_TARGET}" -mindepth 1 -maxdepth 1 -print -quit >/dev/null 2>&1; then
      mkdir -p "${RAG_TARGET}"
      cp -a "${RAG_BACKUP_DIR}/." "${RAG_TARGET}/"
      echo "[restore-local] RAG files restored into ${RAG_TARGET}"
    elif [[ "${force_rag_overwrite}" == "true" ]]; then
      RAG_TARGET_BACKUP="${RAG_TARGET}.bak-$(date +%Y%m%dT%H%M%S)"
      mv "${RAG_TARGET}" "${RAG_TARGET_BACKUP}"
      mkdir -p "${RAG_TARGET}"
      cp -a "${RAG_BACKUP_DIR}/." "${RAG_TARGET}/"
      echo "[restore-local] RAG target moved to ${RAG_TARGET_BACKUP}"
      echo "[restore-local] RAG files restored into ${RAG_TARGET}"
    else
      echo "[restore-local][warn] RAG target already populated; use --force-rag-overwrite to replace it" >&2
    fi
  fi
fi

echo "--- Restoring Model Files ---"
if [[ "${BACKUP_INCLUDE_MODELS}" == "True" || "${BACKUP_INCLUDE_MODELS}" == "true" ]]; then
  MODELS_TARGET="${ROOT_DIR}/models"
  MODELS_BACKUP_DIR="${BACKUP_DIR}/models"
  if [[ -d "${MODELS_BACKUP_DIR}" ]]; then
    mkdir -p "${MODELS_TARGET}"
    cp -a "${MODELS_BACKUP_DIR}/." "${MODELS_TARGET}/"
    echo "[restore-local] Models restored into ${MODELS_TARGET}"
  fi
fi

# Terminate active DB connections
dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" >/dev/null

# Restore DB dump
echo "--- Restoring Database Dump ---"
cat "${POSTGRES_DUMP_FILE}" | dc exec -T postgres pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists --no-owner --no-privileges

# Verify schema version integrity
RESTORED_ALEMBIC_REVISION="$(dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "SELECT version_num FROM alembic_version LIMIT 1;")"
if [[ -n "${BACKUP_ALEMBIC_REVISION}" && "${RESTORED_ALEMBIC_REVISION}" != "${BACKUP_ALEMBIC_REVISION}" ]]; then
  echo "[restore-local][error] Restored schema mismatch: expected ${BACKUP_ALEMBIC_REVISION}, got ${RESTORED_ALEMBIC_REVISION}" >&2
  exit 1
fi

generate_report "SUCCESS"

echo "[restore-local] Restore completed successfully."
exit 0

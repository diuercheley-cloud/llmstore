#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env
cd "${ROOT_DIR}"

usage() {
  cat <<'EOF'
Uso: ./scripts/restore-local.sh [OPÇÕES] /path/to/backup

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
        echo "[restore-local][error] argumento inesperado: $1" >&2
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
  echo "[restore-local][error] backup directory not found: ${BACKUP_DIR}" >&2
  exit 1
fi

MANIFEST_FILE="${BACKUP_DIR}/manifest.json"
CHECKSUM_FILE="${BACKUP_DIR}/checksums.sha256"
POSTGRES_DUMP_FILE="${BACKUP_DIR}/db/postgres.dump"
CONFIG_FILE="${BACKUP_DIR}/config/config.env"

if [[ ! -f "${MANIFEST_FILE}" ]]; then
  echo "[restore-local][error] manifest not found: ${MANIFEST_FILE}" >&2
  exit 1
fi
if [[ ! -f "${POSTGRES_DUMP_FILE}" ]]; then
  echo "[restore-local][error] postgres dump not found: ${POSTGRES_DUMP_FILE}" >&2
  exit 1
fi

echo "[restore-local] validando checksums..."
python3 - "${BACKUP_DIR}" "${CHECKSUM_FILE}" <<'PY'
from __future__ import annotations

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
    expected[backup_dir / rel] = digest

for path, digest in expected.items():
    if not path.exists():
        raise SystemExit(f"[restore-local][error] missing file in backup: {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != digest:
        raise SystemExit(f"[restore-local][error] checksum mismatch: {path}")
PY

MANIFEST_JSON="$(cat "${MANIFEST_FILE}")"
BACKUP_VERSION="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["app_version"])' <<<"${MANIFEST_JSON}")"
BACKUP_ALEMBIC_REVISION="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["alembic_revision"])' <<<"${MANIFEST_JSON}")"
BACKUP_INCLUDE_MODELS="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["include_models"])' <<<"${MANIFEST_JSON}")"
BACKUP_INCLUDE_RAG_FILES="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["include_rag_files"])' <<<"${MANIFEST_JSON}")"
BACKUP_DATE="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read())["created_at"])' <<<"${MANIFEST_JSON}")"

CURRENT_VERSION="$(tr -d '\n' < "${ROOT_DIR}/VERSION")"
if [[ "${BACKUP_VERSION}" != "${CURRENT_VERSION}" ]]; then
  echo "[restore-local][error] backup version mismatch: backup=${BACKUP_VERSION} current=${CURRENT_VERSION}" >&2
  exit 1
fi

if [[ -n "${BACKUP_ALEMBIC_REVISION}" ]] && ! compgen -G "${ROOT_DIR}/control_plane/alembic/versions/*${BACKUP_ALEMBIC_REVISION}*.py" >/dev/null; then
  echo "[restore-local][error] backup alembic revision is not available locally: ${BACKUP_ALEMBIC_REVISION}" >&2
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

if [[ "${dry_run}" == "true" ]]; then
  echo "[restore-local] modo dry-run: validacao concluida com sucesso."
  exit 0
fi

if [[ "${auto_confirm}" != "true" ]]; then
  printf "ATENCAO: Este comando ira destruir os dados atuais do banco de dados.\n"
  printf "Deseja continuar? (y/N) "
  read -r response
  if [[ ! "${response}" =~ ^[Yy]$ ]]; then
    echo "[restore-local] abortado pelo usuario."
    exit 0
  fi
fi

dc up -d postgres redis >/dev/null

for _ in $(seq 1 60); do
  if dc exec -T postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

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
      if ! cp -a "${RAG_BACKUP_DIR}/." "${RAG_TARGET}/"; then
        echo "[restore-local][warn] unable to copy rag files into ${RAG_TARGET}; continuing with database restore only" >&2
      fi
      echo "[restore-local] rag files restored into ${RAG_TARGET}"
    elif [[ "${force_rag_overwrite}" == "true" ]]; then
      RAG_TARGET_BACKUP="${RAG_TARGET}.bak-$(date +%Y%m%dT%H%M%S)"
      mv "${RAG_TARGET}" "${RAG_TARGET_BACKUP}"
      mkdir -p "${RAG_TARGET}"
      if ! cp -a "${RAG_BACKUP_DIR}/." "${RAG_TARGET}/"; then
        echo "[restore-local][error] unable to overwrite rag files into ${RAG_TARGET}" >&2
        exit 1
      fi
      echo "[restore-local] rag target moved to ${RAG_TARGET_BACKUP}"
      echo "[restore-local] rag files restored into ${RAG_TARGET}"
    else
      echo "[restore-local][warn] rag target already populated; use --force-rag-overwrite to replace it" >&2
    fi
  fi
fi

if [[ "${BACKUP_INCLUDE_MODELS}" == "True" || "${BACKUP_INCLUDE_MODELS}" == "true" ]]; then
  MODELS_TARGET="${ROOT_DIR}/models"
  MODELS_BACKUP_DIR="${BACKUP_DIR}/models"
  if [[ -d "${MODELS_BACKUP_DIR}" ]]; then
    mkdir -p "${MODELS_TARGET}"
    cp -a "${MODELS_BACKUP_DIR}/." "${MODELS_TARGET}/"
  fi
fi

dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" >/dev/null
cat "${POSTGRES_DUMP_FILE}" | dc exec -T postgres pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists --no-owner --no-privileges

RESTORED_ALEMBIC_REVISION="$(dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "SELECT version_num FROM alembic_version LIMIT 1;")"
if [[ -n "${BACKUP_ALEMBIC_REVISION}" && "${RESTORED_ALEMBIC_REVISION}" != "${BACKUP_ALEMBIC_REVISION}" ]]; then
  echo "[restore-local][error] restored schema mismatch: expected ${BACKUP_ALEMBIC_REVISION}, got ${RESTORED_ALEMBIC_REVISION}" >&2
  exit 1
fi

printf '[restore-local] success\n'
printf '[restore-local] backup_dir=%s\n' "${BACKUP_DIR}"
printf '[restore-local] restored_revision=%s\n' "${RESTORED_ALEMBIC_REVISION}"
printf '[restore-local] include_models=%s\n' "${BACKUP_INCLUDE_MODELS}"
printf '[restore-local] include_rag_files=%s\n' "${BACKUP_INCLUDE_RAG_FILES}"

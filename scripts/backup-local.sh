#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env
cd "${ROOT_DIR}"

usage() {
  cat <<'EOF'
Uso: ./scripts/backup-local.sh [--include-models] [--include-rag-files] [backup_dir]

Por padrao o backup vai para artifacts/backups-local/<timestamp>.
EOF
}

include_models=false
include_rag_files=false
target_dir=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --include-models)
      include_models=true
      ;;
    --include-rag-files)
      include_rag_files=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -n "${target_dir}" ]]; then
        echo "[backup-local][error] argumento inesperado: $1" >&2
        exit 1
      fi
      target_dir="$1"
      ;;
  esac
  shift
done

BACKUP_ROOT="${ROOT_DIR}/artifacts/backups-local"
TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
TARGET_DIR="${target_dir:-${BACKUP_ROOT}/${TIMESTAMP}}"
mkdir -p "${TARGET_DIR}/db" "${TARGET_DIR}/config"

ENV_SOURCE_FILE="${STACK_ENV_FILE}"
if [[ "${ENV_SOURCE_FILE}" != /* ]]; then
  ENV_SOURCE_FILE="${ROOT_DIR}/${ENV_SOURCE_FILE}"
fi

if [[ ! -f "${ENV_SOURCE_FILE}" ]]; then
  printf '[backup-local][error] env file not found: %s\n' "${ENV_SOURCE_FILE}" >&2
  exit 1
fi

if [[ ! -f "${ROOT_DIR}/VERSION" ]]; then
  printf '[backup-local][error] VERSION file not found: %s\n' "${ROOT_DIR}/VERSION" >&2
  exit 1
fi

POSTGRES_DUMP_FILE="${TARGET_DIR}/db/postgres.dump"
CONFIG_FILE="${TARGET_DIR}/config/config.env"
CHECKSUM_FILE="${TARGET_DIR}/checksums.sha256"
MANIFEST_FILE="${TARGET_DIR}/manifest.json"

ALEMBIC_REVISION="$(dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "SELECT version_num FROM alembic_version LIMIT 1;")"
APP_VERSION="$(tr -d '\n' < "${ROOT_DIR}/VERSION")"

dc exec -T postgres pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc > "${POSTGRES_DUMP_FILE}"

python3 - "${ENV_SOURCE_FILE}" "${CONFIG_FILE}" <<'PY'
from pathlib import Path
import sys

from scripts.local_dr_backup import parse_env_file, sanitize_env_snapshot

env_file = Path(sys.argv[1])
target = Path(sys.argv[2])
env = parse_env_file(env_file)
target.write_text("\n".join(sanitize_env_snapshot(env)) + "\n", encoding="utf-8")
PY

if [[ "${include_models}" == "true" ]]; then
  MODELS_SRC="${ROOT_DIR}/models"
  MODELS_DST="${TARGET_DIR}/models"
  if [[ -d "${MODELS_SRC}" ]]; then
    mkdir -p "${MODELS_DST}"
    cp -a "${MODELS_SRC}/." "${MODELS_DST}/"
  fi
fi

if [[ "${include_rag_files}" == "true" ]]; then
  RAG_STORAGE_DIR="${RAG_STORAGE_DIR:-/data/rag_uploads}"
  RAG_SRC="$(python3 - "${ROOT_DIR}" "${RAG_STORAGE_DIR}" <<'PY'
from pathlib import Path
import sys

from scripts.local_dr_backup import host_path_for_data_dir

root = Path(sys.argv[1])
storage_dir = sys.argv[2]
resolved = host_path_for_data_dir(root, storage_dir)
print(resolved if resolved is not None else "")
PY
)"
  RAG_DST="${TARGET_DIR}/rag_uploads"
  if [[ -n "${RAG_SRC}" && -d "${RAG_SRC}" ]]; then
    mkdir -p "${RAG_DST}"
    cp -a "${RAG_SRC}/." "${RAG_DST}/"
  fi
fi

python3 - "${TARGET_DIR}" "${TIMESTAMP}" "${APP_VERSION}" "${ALEMBIC_REVISION}" "${STACK_MODE:-local}" "${STACK_ENV_FILE}" "${POSTGRES_DUMP_FILE}" "${CONFIG_FILE}" "${CHECKSUM_FILE}" "${MANIFEST_FILE}" "${include_models}" "${include_rag_files}" <<'PY'
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

from scripts.local_dr_backup import (
    BackupManifestInput,
    build_manifest,
    collect_asset_metadata,
    dump_manifest,
)

(
    target_dir,
    timestamp,
    app_version,
    alembic_revision,
    stack_mode,
    env_file,
    dump_file,
    config_file,
    checksums_file,
    manifest_file,
    include_models,
    include_rag_files,
) = sys.argv[1:]

target = Path(target_dir)
include_models_bool = include_models.lower() == "true"
include_rag_files_bool = include_rag_files.lower() == "true"

assets = [
    collect_asset_metadata(Path(dump_file), label="postgres_dump", included=True),
    collect_asset_metadata(Path(config_file), label="config_snapshot", included=True),
    collect_asset_metadata(target / "models", label="model_files", included=include_models_bool),
    collect_asset_metadata(target / "rag_uploads", label="rag_files", included=include_rag_files_bool),
]
if include_models_bool:
    assets[2]["models_dir"] = str(target / "models")
if include_rag_files_bool:
    assets[3]["storage_dir"] = str(target / "rag_uploads")

manifest = build_manifest(
    BackupManifestInput(
        backup_dir=target,
        created_at=timestamp,
        app_version=app_version,
        alembic_revision=alembic_revision,
        stack_mode=stack_mode,
        env_file=env_file,
        dump_file=dump_file,
        config_file=config_file,
        checksums_file=checksums_file,
        include_models=include_models_bool,
        include_rag_files=include_rag_files_bool,
        redis_snapshot_included=False,
        assets=assets,
    )
)
dump_manifest(manifest, manifest_file)

checksum_path = Path(checksums_file)
lines: list[str] = []
for path in sorted(target.rglob("*")):
    if not path.is_file() or path == checksum_path:
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rel = path.relative_to(target)
    lines.append(f"{digest}  {rel}")
checksum_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
PY

printf '[backup-local] success\n'
printf '[backup-local] dir=%s\n' "${TARGET_DIR}"
printf '[backup-local] dump=%s\n' "${POSTGRES_DUMP_FILE}"
printf '[backup-local] manifest=%s\n' "${MANIFEST_FILE}"
printf '[backup-local] config_snapshot=%s\n' "${CONFIG_FILE}"
printf '[backup-local] include_models=%s\n' "${include_models}"
printf '[backup-local] include_rag_files=%s\n' "${include_rag_files}"

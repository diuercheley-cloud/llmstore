#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BACKUP_ROOT="${ROOT_DIR}/artifacts/backups"
TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
TARGET_DIR="${1:-${BACKUP_ROOT}/${TIMESTAMP}}"
mkdir -p "${TARGET_DIR}"

DUMP_FILE="${TARGET_DIR}/postgres.dump"
METADATA_FILE="${TARGET_DIR}/metadata.env"
CHECKSUM_FILE="${TARGET_DIR}/checksums.sha256"
MODEL_MANIFEST_FILE="${TARGET_DIR}/models.manifest.json"
ENV_TARGET_DIR="${TARGET_DIR}/env"
ENV_SOURCE_FILE="${ROOT_DIR}/${STACK_ENV_FILE}"
VERSION_SOURCE_FILE="${ROOT_DIR}/VERSION"
DOCKER_CONFIG_DIR="${TARGET_DIR}/docker-config"

mkdir -p "${ENV_TARGET_DIR}" "${DOCKER_CONFIG_DIR}"

if [[ ! -f "${ENV_SOURCE_FILE}" ]]; then
  printf '[backup][error] env file not found: %s\n' "${ENV_SOURCE_FILE}" >&2
  exit 1
fi

if [[ ! -f "${VERSION_SOURCE_FILE}" ]]; then
  printf '[backup][error] VERSION file not found: %s\n' "${VERSION_SOURCE_FILE}" >&2
  exit 1
fi

ALEMBIC_REVISION="$(dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "SELECT version_num FROM alembic_version LIMIT 1;")"
APP_VERSION="$(tr -d '\n' < "${VERSION_SOURCE_FILE}")"

dc exec -T postgres pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Fc > "${DUMP_FILE}"
cp "${ENV_SOURCE_FILE}" "${ENV_TARGET_DIR}/$(basename "${STACK_ENV_FILE}")"
chmod 600 "${ENV_TARGET_DIR}/$(basename "${STACK_ENV_FILE}")"
cp "${VERSION_SOURCE_FILE}" "${TARGET_DIR}/VERSION"
cp "${ROOT_DIR}/docker-compose.yml" "${DOCKER_CONFIG_DIR}/docker-compose.yml"
if [[ -f "${ROOT_DIR}/docker-compose.prod.yml" ]]; then
  cp "${ROOT_DIR}/docker-compose.prod.yml" "${DOCKER_CONFIG_DIR}/docker-compose.prod.yml"
fi

python3 - "${ROOT_DIR}/models" "${MODEL_MANIFEST_FILE}" <<'PY'
import json
import os
import sys
from pathlib import Path

models_dir = Path(sys.argv[1])
output = Path(sys.argv[2])
entries = []
if models_dir.exists():
    for item in sorted(models_dir.iterdir()):
        if item.is_file():
            stat = item.stat()
            entries.append(
                {
                    "name": item.name,
                    "size_bytes": stat.st_size,
                    "modified_at": int(stat.st_mtime),
                    "copied_in_backup": False,
                }
            )
output.write_text(json.dumps({"models": entries}, indent=2), encoding="utf-8")
PY

cat > "${METADATA_FILE}" <<EOF
timestamp=${TIMESTAMP}
stack_mode=${STACK_MODE:-local}
env_file=${STACK_ENV_FILE}
database=${POSTGRES_DB}
user=${POSTGRES_USER}
app_version=${APP_VERSION}
alembic_revision=${ALEMBIC_REVISION}
model_blobs_included=false
dump_file=$(basename "${DUMP_FILE}")
EOF

(
  cd "${TARGET_DIR}"
  find . -type f ! -name "$(basename "${CHECKSUM_FILE}")" -print0 | sort -z | xargs -0 sha256sum > "${CHECKSUM_FILE}"
)

printf '[backup] success\n'
printf '[backup] dir=%s\n' "${TARGET_DIR}"
printf '[backup] dump=%s\n' "${DUMP_FILE}"
printf '[backup] metadata=%s\n' "${METADATA_FILE}"
printf '[backup] checksums=%s\n' "${CHECKSUM_FILE}"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BACKUP_FILE="${1:?usage: ./scripts/backup/restore.sh /path/to/postgres.dump}"
if [[ ! -f "${BACKUP_FILE}" ]]; then
  if [[ ! -d "${BACKUP_FILE}" ]]; then
    echo "backup file or backup directory not found: ${BACKUP_FILE}" >&2
    exit 1
  fi
fi

BACKUP_DIR=""
DUMP_FILE=""
METADATA_FILE=""
CHECKSUM_FILE=""
BACKUP_VERSION=""
BACKUP_ALEMBIC_REVISION=""
RESTORE_ENV_CHOICE="${RESTORE_ENV_CHOICE:-prompt}"
RESTORE_CONFIRMATION="${RESTORE_CONFIRMATION:-}"
CURRENT_VERSION="$(tr -d '\n' < "${ROOT_DIR}/VERSION")"
CURRENT_ENV_PATH="${ROOT_DIR}/${STACK_ENV_FILE}"

latest_local_revision() {
  ls "${ROOT_DIR}/control_plane/alembic/versions"/*.py 2>/dev/null | sed -E 's#.*/([0-9]{8}_[0-9]{4}).*#\1#' | sort | tail -n1
}

parse_backup_layout() {
  if [[ -d "${BACKUP_FILE}" ]]; then
    BACKUP_DIR="${BACKUP_FILE}"
    DUMP_FILE="${BACKUP_DIR}/postgres.dump"
    METADATA_FILE="${BACKUP_DIR}/metadata.env"
    CHECKSUM_FILE="${BACKUP_DIR}/checksums.sha256"
  else
    BACKUP_DIR="$(cd "$(dirname "${BACKUP_FILE}")" && pwd)"
    DUMP_FILE="${BACKUP_FILE}"
    METADATA_FILE="${BACKUP_DIR}/metadata.env"
    CHECKSUM_FILE="${BACKUP_DIR}/checksums.sha256"
  fi
  [[ -f "${DUMP_FILE}" ]] || { echo "postgres dump not found: ${DUMP_FILE}" >&2; exit 1; }
}

verify_checksums() {
  if [[ -f "${CHECKSUM_FILE}" ]]; then
    (cd "${BACKUP_DIR}" && sha256sum -c "$(basename "${CHECKSUM_FILE}")") >/dev/null
  fi
}

load_metadata() {
  [[ -f "${METADATA_FILE}" ]] || { echo "backup metadata not found: ${METADATA_FILE}" >&2; exit 1; }
  # shellcheck disable=SC1090
  source "${METADATA_FILE}"
  BACKUP_VERSION="${app_version:-unknown}"
  BACKUP_ALEMBIC_REVISION="${alembic_revision:-}"
}

validate_version_and_schema() {
  local local_revision
  local_revision="$(latest_local_revision)"
  [[ -n "${BACKUP_ALEMBIC_REVISION}" ]] || { echo "backup metadata missing alembic revision" >&2; exit 1; }
  compgen -G "${ROOT_DIR}/control_plane/alembic/versions/*${BACKUP_ALEMBIC_REVISION}*.py" >/dev/null || {
    echo "backup alembic revision is not available locally: ${BACKUP_ALEMBIC_REVISION}" >&2
    exit 1
  }
  if [[ "${BACKUP_VERSION}" != "${CURRENT_VERSION}" ]]; then
    echo "backup version mismatch: backup=${BACKUP_VERSION} current=${CURRENT_VERSION}" >&2
    exit 1
  fi
  if [[ "${BACKUP_ALEMBIC_REVISION}" != "${local_revision}" ]]; then
    echo "backup schema mismatch: backup=${BACKUP_ALEMBIC_REVISION} local_head=${local_revision}" >&2
    exit 1
  fi
}

confirm_restore() {
  cat <<EOF
[restore] target database: ${POSTGRES_DB}
[restore] backup source: ${BACKUP_DIR}
[restore] backup version: ${BACKUP_VERSION}
[restore] backup alembic revision: ${BACKUP_ALEMBIC_REVISION}
[restore] this will overwrite objects in the current database
EOF
  if [[ "${RESTORE_CONFIRMATION}" == "RESTORE" ]]; then
    return 0
  fi
  printf '[restore] type RESTORE to continue: '
  read -r typed
  [[ "${typed}" == "RESTORE" ]] || { echo "[restore] aborted" >&2; exit 1; }
}

maybe_restore_env() {
  local backup_env_file
  backup_env_file="$(find "${BACKUP_DIR}/env" -maxdepth 1 -type f | head -n1 || true)"
  [[ -n "${backup_env_file}" ]] || return 0
  case "${RESTORE_ENV_CHOICE}" in
    yes)
      ;;
    no)
      return 0
      ;;
    prompt)
      printf '[restore] overwrite %s with backup env file %s? [y/N]: ' "${CURRENT_ENV_PATH}" "${backup_env_file}"
      read -r reply
      [[ "${reply}" =~ ^[Yy]$ ]] || return 0
      ;;
    *)
      echo "[restore] invalid RESTORE_ENV_CHOICE=${RESTORE_ENV_CHOICE}" >&2
      exit 1
      ;;
  esac
  cp "${backup_env_file}" "${CURRENT_ENV_PATH}"
  chmod 600 "${CURRENT_ENV_PATH}"
  printf '[restore] env restored to %s\n' "${CURRENT_ENV_PATH}"
}

parse_backup_layout
verify_checksums
load_metadata
validate_version_and_schema
confirm_restore

maybe_restore_env

dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" >/dev/null
cat "${DUMP_FILE}" | dc exec -T postgres pg_restore -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" --clean --if-exists --no-owner --no-privileges

RESTORED_ALEMBIC_REVISION="$(dc exec -T postgres psql -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -Atc "SELECT version_num FROM alembic_version LIMIT 1;")"
if [[ "${RESTORED_ALEMBIC_REVISION}" != "${BACKUP_ALEMBIC_REVISION}" ]]; then
  echo "[restore] restored schema mismatch: expected ${BACKUP_ALEMBIC_REVISION}, got ${RESTORED_ALEMBIC_REVISION}" >&2
  exit 1
fi

printf '[restore] success\n'
printf '[restore] restored_revision=%s\n' "${RESTORED_ALEMBIC_REVISION}"

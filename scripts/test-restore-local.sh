#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env
cd "${ROOT_DIR}"

tmp_root="$(mktemp -d "/tmp/llmstack-test-restore-XXXXXX")"
fake_bin="${tmp_root}/bin"
backup_dir="${tmp_root}/backup"
rag_target="${tmp_root}/rag-target"
env_file="${tmp_root}/test.env"
mkdir -p "${fake_bin}" "${backup_dir}/db" "${backup_dir}/config" "${backup_dir}/rag_uploads/client-a" "${rag_target}"

cleanup() {
  rm -rf "${tmp_root}"
}
trap cleanup EXIT

cat > "${fake_bin}/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "compose" ]]; then
  exit 0
fi
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    exec)
      shift
      while [[ $# -gt 0 && "$1" == -* ]]; do
        shift
      done
      service="${1:-}"
      shift || true
      cmd="${1:-}"
      if [[ "${service}" == "postgres" && "${cmd}" == "pg_isready" ]]; then
        exit 0
      fi
      if [[ "${service}" == "postgres" && "${cmd}" == "psql" ]]; then
        if printf '%s\n' "$*" | grep -q 'version_num'; then
          printf '%s\n' "${FAKE_ALEMBIC_REVISION}"
        fi
        exit 0
      fi
      if [[ "${service}" == "postgres" && "${cmd}" == "pg_restore" ]]; then
        cat >/dev/null
        exit 0
      fi
      exit 0
      ;;
    up|down|logs)
      exit 0
      ;;
    *)
      shift
      ;;
  esac
done
EOF
chmod +x "${fake_bin}/docker"

cat > "${env_file}" <<EOF
ADMIN_TOKEN=test-admin-token
POSTGRES_USER=postgres
POSTGRES_DB=llm_gateway
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/llm_gateway
REDIS_URL=redis://redis:6379/0
HOST_PORT=18080
RAG_STORAGE_DIR=${rag_target}
EOF

revision="$(python3 - <<'PY'
from pathlib import Path
import re

versions = sorted(Path("control_plane/alembic/versions").glob("*.py"))
for path in versions:
    match = re.match(r"(\d{8}_\d{4})_", path.name)
    if match:
        print(match.group(1))
        break
PY
)"
if [[ -z "${revision}" ]]; then
  echo "[test-restore-local][error] could not determine alembic revision" >&2
  exit 1
fi
app_version="$(tr -d '\n' < VERSION)"
export FAKE_ALEMBIC_REVISION="${revision}"

printf 'fake postgres dump\n' > "${backup_dir}/db/postgres.dump"
printf 'HOST_PORT=18080\n' > "${backup_dir}/config/config.env"
printf 'rag file\n' > "${backup_dir}/rag_uploads/client-a/doc.txt"
(
  cd "${backup_dir}"
  sha256sum db/postgres.dump config/config.env rag_uploads/client-a/doc.txt > checksums.sha256
)
cat > "${backup_dir}/manifest.json" <<EOF
{
  "created_at": "2026-05-07T12:00:00Z",
  "app_version": "${app_version}",
  "alembic_revision": "${revision}",
  "stack_mode": "local",
  "env_file": ".env.local",
  "backup_dir": "${backup_dir}",
  "include_models": false,
  "include_rag_files": true,
  "redis_snapshot_included": false,
  "files": {
    "postgres_dump": "${backup_dir}/db/postgres.dump",
    "config_snapshot": "${backup_dir}/config/config.env",
    "checksums": "${backup_dir}/checksums.sha256"
  },
  "assets": [
    {
      "label": "postgres_dump",
      "included": true,
      "exists": true,
      "path": "${backup_dir}/db/postgres.dump",
      "type": "file",
      "name": "postgres.dump",
      "size_bytes": 18
    },
    {
      "label": "config_snapshot",
      "included": true,
      "exists": true,
      "path": "${backup_dir}/config/config.env",
      "type": "file",
      "name": "config.env",
      "size_bytes": 16
    },
    {
      "label": "rag_files",
      "included": true,
      "exists": true,
      "path": "${backup_dir}/rag_uploads",
      "storage_dir": "${rag_target}",
      "type": "directory",
      "name": "rag_uploads",
      "file_count": 1,
      "size_bytes": 8
    }
  ]
}
EOF

export PATH="${fake_bin}:${PATH}"
export ENV_FILE="${env_file}"

printf 'old rag file\n' > "${rag_target}/sentinel.txt"

no_force_output="$("${SCRIPT_DIR}/restore-local.sh" "${backup_dir}" 2>&1)"
printf '%s\n' "${no_force_output}"
if ! printf '%s\n' "${no_force_output}" | grep -q 'use --force-rag-overwrite to replace it'; then
  echo "[test-restore-local][error] missing overwrite warning" >&2
  exit 1
fi
if [[ ! -f "${rag_target}/sentinel.txt" ]]; then
  echo "[test-restore-local][error] sentinel should remain without force" >&2
  exit 1
fi
if [[ -f "${rag_target}/client-a/doc.txt" ]]; then
  echo "[test-restore-local][error] rag file should not be copied without force" >&2
  exit 1
fi

force_output="$("${SCRIPT_DIR}/restore-local.sh" --force-rag-overwrite "${backup_dir}" 2>&1)"
printf '%s\n' "${force_output}"
if ! printf '%s\n' "${force_output}" | grep -q 'rag target moved to'; then
  echo "[test-restore-local][error] missing force overwrite message" >&2
  exit 1
fi
if [[ ! -f "${rag_target}/client-a/doc.txt" ]]; then
  echo "[test-restore-local][error] rag file was not restored with force" >&2
  exit 1
fi
if ! compgen -G "${rag_target}.bak-*" >/dev/null; then
  echo "[test-restore-local][error] backup of previous rag dir not created" >&2
  exit 1
fi

printf '[test-restore-local] success\n'
printf '[test-restore-local] backup_dir=%s\n' "${backup_dir}"
printf '[test-restore-local] rag_target=%s\n' "${rag_target}"

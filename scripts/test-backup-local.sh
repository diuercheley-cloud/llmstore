#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env
cd "${ROOT_DIR}"

tmp_root="$(mktemp -d "/tmp/llmstack-test-backup-XXXXXX")"
fake_bin="${tmp_root}/bin"
mkdir -p "${fake_bin}"

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
      if [[ "${service}" == "postgres" && "${cmd}" == "pg_dump" ]]; then
        printf 'TEST_PGDUMP\n'
        exit 0
      fi
      if [[ "${service}" == "postgres" && "${cmd}" == "psql" ]]; then
        if printf '%s\n' "$*" | grep -q 'version_num'; then
          printf '20260505_0016\n'
        fi
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

env_file="${tmp_root}/test.env"
cat > "${env_file}" <<'EOF'
ADMIN_TOKEN=test-admin-token
POSTGRES_USER=postgres
POSTGRES_DB=llm_gateway
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/llm_gateway
REDIS_URL=redis://redis:6379/0
HOST_PORT=18080
EOF

export PATH="${fake_bin}:${PATH}"
export ENV_FILE="${env_file}"

backup_output="$("${SCRIPT_DIR}/backup-local.sh" 2>&1)"
printf '%s\n' "${backup_output}"
backup_dir="$(printf '%s\n' "${backup_output}" | awk -F= '/^\[backup-local\] dir=/{print $2}' | tail -n1)"

if [[ -z "${backup_dir}" || ! -d "${backup_dir}" ]]; then
  echo "[test-backup-local][error] backup dir not found" >&2
  exit 1
fi

for expected in "${backup_dir}/db/postgres.dump" "${backup_dir}/manifest.json" "${backup_dir}/config/config.env"; do
  if [[ ! -f "${expected}" ]]; then
    echo "[test-backup-local][error] missing ${expected}" >&2
    exit 1
  fi
done

python3 - "${backup_dir}/manifest.json" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert manifest["files"]["postgres_dump"].endswith("db/postgres.dump")
assert manifest["files"]["config_snapshot"].endswith("config/config.env")
assert manifest["include_models"] is False
assert manifest["include_rag_files"] is False
PY

printf '[test-backup-local] success\n'
printf '[test-backup-local] backup_dir=%s\n' "${backup_dir}"

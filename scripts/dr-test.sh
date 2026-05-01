#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BACKUP_ROOT="${ROOT_DIR}/artifacts/backups"
REPORT_ROOT="${ROOT_DIR}/artifacts/dr-tests"
TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
BACKUP_DIR="${1:-$(find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d | sort | tail -n1)}"
[[ -n "${BACKUP_DIR}" && -d "${BACKUP_DIR}" ]] || { echo "[dr-test][error] backup directory not found" >&2; exit 1; }

REPORT_DIR="${REPORT_ROOT}/${TIMESTAMP}"
mkdir -p "${REPORT_DIR}"

TEMP_ENV_FILE="/tmp/llm-inference-stack-dr-${TIMESTAMP}.env"
TEMP_OVERRIDE_FILE="/tmp/llm-inference-stack-dr-${TIMESTAMP}.override.yml"
PROJECT_NAME="llmstackdr$(printf '%s' "${TIMESTAMP}" | tr '[:upper:]' '[:lower:]')"
DR_HOST_PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
export DR_HOST_PORT
BASE_URL="http://localhost:${DR_HOST_PORT}"
BACKUP_ENV_FILE="$(find "${BACKUP_DIR}/env" -maxdepth 1 -type f | head -n1 || true)"
[[ -n "${BACKUP_ENV_FILE}" ]] || { echo "[dr-test][error] backup env file not found in ${BACKUP_DIR}/env" >&2; exit 1; }

cleanup() {
  local status=$?
  docker compose -p "${PROJECT_NAME}" down -v >/dev/null 2>&1 || true
  if [[ -f "${TEMP_ENV_FILE}" ]]; then
    rm -f "${TEMP_ENV_FILE}"
  fi
  rm -f "${TEMP_OVERRIDE_FILE}"
  exit "${status}"
}
trap cleanup EXIT

cp "${BACKUP_ENV_FILE}" "${TEMP_ENV_FILE}"
chmod 600 "${TEMP_ENV_FILE}"
python3 - "${TEMP_ENV_FILE}" <<'PY'
from pathlib import Path
import os
import sys

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
updates = {
    "HOST_PORT": os.environ["DR_HOST_PORT"],
    "POSTGRES_PORT": "15432",
    "REDIS_PORT": "16379",
    "PROMETHEUS_PORT": "19090",
    "GRAFANA_PORT": "13001",
    "PUBLIC_EXPOSURE": "false",
}
result = []
seen = set()
for line in lines:
    if "=" in line and not line.startswith("#"):
        key, _, value = line.partition("=")
        if key in updates:
            result.append(f"{key}={updates[key]}")
            seen.add(key)
            continue
    result.append(line)
for key, value in updates.items():
    if key not in seen:
        result.append(f"{key}={value}")
path.write_text("\n".join(result) + "\n", encoding="utf-8")
PY

cat > "${TEMP_OVERRIDE_FILE}" <<'EOF'
services:
  postgres:
    ports: !reset []
  redis:
    ports: !reset []
  data-plane-gemma:
    ports: !reset []
EOF

ENV_FILE="${TEMP_ENV_FILE}"
export ENV_FILE
export COMPOSE_PROJECT_NAME="${PROJECT_NAME}"
export EXTRA_COMPOSE_FILES="${TEMP_OVERRIDE_FILE}"
init_stack_env
export HOST_PORT="${DR_HOST_PORT}"
export PROMETHEUS_PORT=19090
export GRAFANA_PORT=13001
export PUBLIC_EXPOSURE=false

log_step() {
  printf '[dr-test] %s\n' "$*"
}

wait_url() {
  local url="$1"
  local attempts="${2:-90}"
  for _ in $(seq 1 "${attempts}"); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 3
  done
  return 1
}

log_step "starting temporary clean environment"
dc up -d --build >"${REPORT_DIR}/compose-up.log" 2>&1

log_step "restoring backup"
RESTORE_CONFIRMATION=RESTORE RESTORE_ENV_CHOICE=no "${SCRIPT_DIR}/restore.sh" "${BACKUP_DIR}" >"${REPORT_DIR}/restore.log" 2>&1

log_step "restarting control plane after restore"
dc restart control-plane control-plane-worker >"${REPORT_DIR}/compose-restart.log" 2>&1

log_step "waiting for health and readiness"
wait_url "${BASE_URL}/health" || { echo "[dr-test][error] health failed" >&2; exit 1; }
wait_url "${BASE_URL}/ready" || { echo "[dr-test][error] ready failed" >&2; exit 1; }
curl -fsS "${BASE_URL}/health" >"${REPORT_DIR}/health.json"
curl -fsS "${BASE_URL}/ready" >"${REPORT_DIR}/ready.json"

log_step "issuing demo api key and testing chat"
API_KEY="$(issue_demo_api_key "${BASE_URL}" "dr-test" || true)"
[[ -n "${API_KEY}" ]] || { echo "[dr-test][error] could not issue demo key" >&2; exit 1; }
curl -fsS "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Responda com uma frase curta: o restore de desastre funcionou?"}],
    "max_tokens": 64,
    "stream": false,
    "include_reasoning": false
  }' >"${REPORT_DIR}/chat.json"

cat > "${REPORT_DIR}/report.txt" <<EOF
dr_test_timestamp=${TIMESTAMP}
backup_dir=${BACKUP_DIR}
project_name=${PROJECT_NAME}
env_file=${TEMP_ENV_FILE}
base_url=${BASE_URL}
health_status=ok
ready_status=ok
chat_test=ok
report_dir=${REPORT_DIR}
EOF

log_step "cleaning temporary environment"
dc down -v >"${REPORT_DIR}/cleanup.log" 2>&1
rm -f "${TEMP_ENV_FILE}" "${TEMP_OVERRIDE_FILE}"
trap - EXIT

printf '[dr-test] success\n'
printf '[dr-test] report=%s\n' "${REPORT_DIR}/report.txt"

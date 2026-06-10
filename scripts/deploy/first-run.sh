#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

log() {
  printf '[first-run] %s\n' "$*"
}

fail() {
  printf '[first-run][error] %s\n' "$*" >&2
  exit 1
}

random_token() {
  python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
}

ensure_env_file() {
  local env_path="${ROOT_DIR}/${STACK_ENV_FILE}"
  if [[ ! -f "${env_path}" ]]; then
    cp "${ROOT_DIR}/.env.example" "${env_path}"
    log "created ${STACK_ENV_FILE} from .env.example"
  fi
  chmod 600 "${env_path}"

  if grep -q '^ADMIN_TOKEN=change-this-admin-token$' "${env_path}"; then
    local new_admin_token="admin-$(random_token)"
    sed -i "s|^ADMIN_TOKEN=.*$|ADMIN_TOKEN=${new_admin_token}|" "${env_path}"
    log "generated ADMIN_TOKEN in ${STACK_ENV_FILE}"
  fi

  if grep -q '^POSTGRES_PASSWORD=llm_gateway_dev_password$' "${env_path}"; then
    local new_db_password="db-$(random_token)"
    sed -i "s|^POSTGRES_PASSWORD=.*$|POSTGRES_PASSWORD=${new_db_password}|" "${env_path}"
    sed -i "s|^DATABASE_URL=.*$|DATABASE_URL=postgresql+asyncpg://llm_gateway:${new_db_password}@postgres:5432/llm_gateway|" "${env_path}"
    log "generated POSTGRES_PASSWORD in ${STACK_ENV_FILE}"
  fi
}

validate_gpu() {
  log "validating gpu visibility"
  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi || true
  else
    log "nvidia-smi not found on host; continuing"
  fi
  if docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi >/tmp/first-run-gpu.txt 2>&1; then
    tail -n 10 /tmp/first-run-gpu.txt || true
  else
    fail "docker GPU validation failed; inspect /tmp/first-run-gpu.txt"
  fi
}

ensure_model() {
  if [[ -f "${ROOT_DIR}/models/${MODEL_FILE}" ]]; then
    log "model already present: models/${MODEL_FILE}"
    return
  fi
  log "model not found; downloading ${MODEL_FILE}"
  "${SCRIPT_DIR}/download-model.sh"
}

wait_ready() {
  local base_url
  base_url="${BASE_URL:-$(default_base_url)}"
  for _ in $(seq 1 90); do
    if curl -fsS "${base_url}/ready" >/tmp/first-run-ready.json 2>/dev/null; then
      return 0
    fi
    sleep 5
  done
  fail "stack did not become ready in time"
}

ensure_default_plan() {
  local base_url="${BASE_URL:-$(default_base_url)}"
  local status
  status="$(curl -sS -o /tmp/first-run-plan.json -w '%{http_code}' -X POST "${base_url}/admin/billing/plans" \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"code":"starter","name":"Starter","description":"Plano padrão do first-run","rate_limit_per_minute":8,"daily_token_quota":40000,"monthly_token_quota":400000,"max_output_tokens":512,"allow_streaming":true}' || true)"
  if [[ "${status}" == "200" || "${status}" == "201" || "${status}" == "409" ]]; then
    log "default commercial plan checked"
    return
  fi
  fail "failed to create/check default plan; status=${status}"
}

create_demo_customer() {
  "${SCRIPT_DIR}/../dev/create-customer-demo.sh" "customer-demo" "cliente demo do first-run" "basic"
}

print_summary() {
  local base_url="${BASE_URL:-$(default_base_url)}"
  local admin_dashboard_url="${base_url}/admin-dashboard"
  local client_portal_url="${base_url}/client-portal"
  local api_output="$1"
  local api_key
  api_key="$(printf '%s\n' "${api_output}" | awk -F= '/^api_key=/{print $2}' | tail -n1)"
  printf '\n[first-run][summary] env_file=%s\n' "${STACK_ENV_FILE}"
  printf '[first-run][summary] base_url=%s\n' "${base_url}"
  printf '[first-run][summary] admin_dashboard=%s\n' "${admin_dashboard_url}"
  printf '[first-run][summary] client_portal=%s\n' "${client_portal_url}"
  printf '[first-run][summary] openai_chat_endpoint=%s/v1/chat/completions\n' "${base_url}"
  printf '[first-run][summary] demo_api_key=%s\n' "${api_key}"
  printf '[first-run][summary] warning=store this api key securely; it is shown only in this script output\n'
}

ensure_env_file
init_stack_env

log "using env file ${STACK_ENV_FILE}"
validate_gpu
ensure_model

log "starting stack"
"${SCRIPT_DIR}/up.sh"

log "waiting for readiness"
wait_ready

log "ensuring default plan"
ensure_default_plan

log "creating demo customer"
demo_output="$(create_demo_customer)"
printf '%s\n' "${demo_output}"

print_summary "${demo_output}"

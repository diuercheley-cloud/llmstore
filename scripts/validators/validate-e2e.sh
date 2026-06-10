#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

ARTIFACTS_DIR="${ROOT_DIR}/artifacts/validation/$(date +%Y%m%dT%H%M%S)"
mkdir -p "${ARTIFACTS_DIR}"

log() {
  printf '[validate] %s\n' "$*"
}

fail() {
  local message="$1"
  local service="${2:-}"
  local suggestion="${3:-}"
  printf '[validate][error] %s\n' "${message}" >&2
  if [[ -n "${service}" ]]; then
    printf '[validate][error] service=%s\n' "${service}" >&2
    dc logs --tail=120 "${service}" >"${ARTIFACTS_DIR}/${service}.tail.log" 2>&1 || true
    printf '[validate][error] last-log=%s\n' "${ARTIFACTS_DIR}/${service}.tail.log" >&2
    tail -n 40 "${ARTIFACTS_DIR}/${service}.tail.log" >&2 || true
  fi
  if [[ -n "${suggestion}" ]]; then
    printf '[validate][error] suggested-command=%s\n' "${suggestion}" >&2
  fi
  exit 1
}

wait_http_json() {
  local url="$1"
  local output="$2"
  local attempts="${3:-60}"
  local sleep_seconds="${4:-5}"
  local status_code
  local curl_args=(-sS -o "${output}" -w '%{http_code}')
  if [[ "${url}" == https://localhost* ]] || [[ "${url}" == https://127.0.0.1* ]]; then
    curl_args=(-k "${curl_args[@]}")
  fi
  for _ in $(seq 1 "${attempts}"); do
    status_code="$(curl "${curl_args[@]}" "${url}" || true)"
    if [[ "${status_code}" == "200" ]]; then
      return 0
    fi
    sleep "${sleep_seconds}"
  done
  return 1
}

ROOT_DIR_ESCAPED="${ROOT_DIR}"
cd "${ROOT_DIR_ESCAPED}"

BASE_URL="${BASE_URL:-$(default_base_url)}"

log "checking docker"
docker info >"${ARTIFACTS_DIR}/docker-info.txt" 2>&1 || fail "docker daemon unavailable" "" "docker info"
dc config >"${ARTIFACTS_DIR}/compose-config.yml" 2>&1 || fail "docker compose config failed" "" "docker compose config"

log "checking gpu access"
nvidia-smi >"${ARTIFACTS_DIR}/host-nvidia-smi.txt" 2>&1 || true
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi >"${ARTIFACTS_DIR}/docker-nvidia-smi.txt" 2>&1 \
  || fail "docker GPU runtime is not working" "" "docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi"

log "checking environment files"
[[ -f "${STACK_ENV_FILE}" ]] || fail "env file missing: ${STACK_ENV_FILE}" "" "cp .env.example ${STACK_ENV_FILE}"
env_perms="$(stat -c '%a' "${STACK_ENV_FILE}" 2>/dev/null || true)"
[[ "${env_perms}" == "600" ]] || fail "env file permissions must be 600" "" "chmod 600 ${STACK_ENV_FILE}"
env_model_file="$(awk -F= '/^MODEL_FILE=/{print $2}' "${STACK_ENV_FILE}" | tail -n1)"
[[ -n "${env_model_file}" ]] || fail "MODEL_FILE missing from .env" "" "edit .env"
[[ -f "models/${env_model_file}" ]] || fail "model file not found: models/${env_model_file}" "" "./scripts/deploy/download-model.sh"

log "building and starting containers"
dc up -d --build >"${ARTIFACTS_DIR}/compose-up.log" 2>&1 || fail "docker compose up failed" "" "docker compose up -d --build"

log "capturing startup logs"
dc logs control-plane >"${ARTIFACTS_DIR}/control-plane.log" 2>&1 || true
dc logs control-plane-worker >"${ARTIFACTS_DIR}/control-plane-worker.log" 2>&1 || true
dc logs data-plane-gemma >"${ARTIFACTS_DIR}/data-plane-gemma.log" 2>&1 || true
dc logs postgres >"${ARTIFACTS_DIR}/postgres.log" 2>&1 || true
dc logs redis >"${ARTIFACTS_DIR}/redis.log" 2>&1 || true

log "waiting for health and readiness"
wait_http_json "${BASE_URL}/health" "${ARTIFACTS_DIR}/health.json" 60 5 || fail "health endpoint did not return 200" "control-plane" "docker compose logs -f control-plane"
wait_http_json "${BASE_URL}/ready" "${ARTIFACTS_DIR}/ready.json" 90 5 || fail "ready endpoint did not return 200" "control-plane" "docker compose logs -f control-plane"

log "issuing demo api key via admin api"
DEMO_CLIENT_ID="$(lookup_demo_client_id "${BASE_URL}" || true)"
[[ -n "${DEMO_CLIENT_ID}" ]] || fail "demo client not found via admin API" "control-plane" "curl -H 'X-Admin-Token: ...' ${BASE_URL}/admin/clients"
API_KEY="$(issue_demo_api_key "${BASE_URL}" "validate-e2e" || true)"
[[ -n "${API_KEY}" ]] || fail "demo API key could not be obtained" "control-plane" "curl -H 'X-Admin-Token: ...' ${BASE_URL}/admin/api-keys"
printf '%s\n' "${API_KEY}" >"${ARTIFACTS_DIR}/demo-api-key.txt"

log "testing models endpoint"
curl_base_url "${BASE_URL}/v1/models" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  >"${ARTIFACTS_DIR}/models.json" \
  || fail "v1/models failed" "control-plane" "curl -H 'Authorization: Bearer ...' ${BASE_URL}/v1/models"

log "testing chat completion"
curl_base_url "${BASE_URL}/v1/chat/completions" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Responda com uma frase curta: o servidor está funcional?"}],
    "max_tokens": 96,
    "stream": false,
    "include_reasoning": false
  }' >"${ARTIFACTS_DIR}/chat.json" \
  || fail "chat completion failed" "control-plane" "./scripts/dev/test-chat.sh"
if grep -q 'reasoning_content' "${ARTIFACTS_DIR}/chat.json"; then
  fail "chat completion leaked reasoning_content with default filtering" "control-plane" "cat ${ARTIFACTS_DIR}/chat.json"
fi

log "testing async chat completion"
curl_base_url "${BASE_URL}/v1/chat/completions/async" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Responda com uma frase curta: o worker async está funcional?"}],
    "max_tokens": 96,
    "stream": false,
    "include_reasoning": false
  }' >"${ARTIFACTS_DIR}/async-chat.json" \
  || fail "async chat enqueue failed" "control-plane" "./scripts/dev/async-chat.sh"
ASYNC_JOB_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' "${ARTIFACTS_DIR}/async-chat.json")"
for _ in $(seq 1 60); do
  curl_base_url "${BASE_URL}/v1/jobs/${ASYNC_JOB_ID}" -fsS \
    -H "Authorization: Bearer ${API_KEY}" >"${ARTIFACTS_DIR}/async-job-status.json" \
    || fail "async job status failed" "control-plane" "./scripts/dev/job-status.sh ${ASYNC_JOB_ID}"
  ASYNC_JOB_STATUS="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "${ARTIFACTS_DIR}/async-job-status.json")"
  if [[ "${ASYNC_JOB_STATUS}" == "completed" ]]; then
    break
  fi
  if [[ "${ASYNC_JOB_STATUS}" == "failed" || "${ASYNC_JOB_STATUS}" == "cancelled" ]]; then
    fail "async job finished with unexpected status ${ASYNC_JOB_STATUS}" "control-plane-worker" "cat ${ARTIFACTS_DIR}/async-job-status.json"
  fi
  sleep 2
done
[[ "${ASYNC_JOB_STATUS}" == "completed" ]] || fail "async job did not complete in time" "control-plane-worker" "cat ${ARTIFACTS_DIR}/async-job-status.json"

log "testing streaming"
curl_base_url "${BASE_URL}/v1/chat/completions" -N -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Conte de 1 a 5 em portugues."}],
    "max_tokens": 64,
    "stream": true,
    "include_reasoning": false
  }' >"${ARTIFACTS_DIR}/stream.txt" \
  || fail "streaming chat failed" "control-plane" "./scripts/dev/test-stream.sh"
if grep -q 'reasoning_content' "${ARTIFACTS_DIR}/stream.txt"; then
  fail "streaming chat leaked reasoning_content with default filtering" "control-plane" "cat ${ARTIFACTS_DIR}/stream.txt"
fi

log "testing invoice generation and listing"
curl_base_url "${BASE_URL}/admin/billing/invoices/generate" -fsS \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"due_in_days":7,"payment_method":"manual_pix","payment_instructions":"validate-e2e"}' \
  >"${ARTIFACTS_DIR}/invoices-generate.json" \
  || fail "invoice generation failed" "control-plane" "./scripts/dev/generate-invoices.sh"
curl_base_url "${BASE_URL}/admin/billing/invoices" -fsS \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  >"${ARTIFACTS_DIR}/invoices-list.json" \
  || fail "invoice list failed" "control-plane" "curl -H 'X-Admin-Token: ...' ${BASE_URL}/admin/billing/invoices"

log "testing billing cycle endpoint"
curl_base_url "${BASE_URL}/admin/billing/run-cycle" -fsS \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -X POST \
  >"${ARTIFACTS_DIR}/billing-cycle.json" \
  || fail "billing cycle failed" "control-plane" "./scripts/dev/run-billing-cycle.sh"

log "testing correlation id and security endpoints"
curl_base_url "${BASE_URL}/v1/models" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "X-Correlation-ID: validate-corr-id" \
  -D "${ARTIFACTS_DIR}/models.headers.txt" \
  -o /dev/null \
  || fail "models with correlation id failed" "control-plane" "curl -H 'X-Correlation-ID: ...' ${BASE_URL}/v1/models"
grep -qi '^X-Correlation-ID: validate-corr-id' "${ARTIFACTS_DIR}/models.headers.txt" \
  || fail "correlation id header missing in response" "control-plane" "cat ${ARTIFACTS_DIR}/models.headers.txt"
curl_base_url "${BASE_URL}/admin/security/events" -fsS \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  >"${ARTIFACTS_DIR}/security-events.json" \
  || fail "security events endpoint failed" "control-plane" "./scripts/dev/security-events.sh"

log "testing exports and monthly report"
curl_base_url "${BASE_URL}/admin/export/usage?format=json" -fsS \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  >"${ARTIFACTS_DIR}/export-usage.json" \
  || fail "usage export json failed" "control-plane" "./scripts/dev/export-usage.sh"
curl_base_url "${BASE_URL}/admin/export/request-logs?format=csv" -fsS \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  >"${ARTIFACTS_DIR}/export-request-logs.csv" \
  || fail "request log export csv failed" "control-plane" "curl -H 'X-Admin-Token: ...' ${BASE_URL}/admin/export/request-logs?format=csv"
grep -q 'client_id' "${ARTIFACTS_DIR}/export-request-logs.csv" \
  || fail "request log export csv missing header" "control-plane" "cat ${ARTIFACTS_DIR}/export-request-logs.csv"
curl_base_url "${BASE_URL}/admin/reports/monthly" -fsS \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  >"${ARTIFACTS_DIR}/monthly-report.json" \
  || fail "monthly report endpoint failed" "control-plane" "./scripts/validators/monthly-report.sh"

log "testing security suspend and unsuspend"
curl_base_url "${BASE_URL}/admin/security/clients/${DEMO_CLIENT_ID}/suspend" -fsS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  >"${ARTIFACTS_DIR}/suspend-client.json" \
  || fail "suspend client endpoint failed" "control-plane" "./scripts/dev/suspend-client.sh ${DEMO_CLIENT_ID}"
blocked_status="$(curl_base_url "${BASE_URL}/v1/models" -sS -o /dev/null -w '%{http_code}' -H "Authorization: Bearer ${API_KEY}" || true)"
[[ "${blocked_status}" == "403" ]] || fail "suspended client still accessed models endpoint" "control-plane" "cat ${ARTIFACTS_DIR}/suspend-client.json"
curl_base_url "${BASE_URL}/admin/security/clients/${DEMO_CLIENT_ID}/unsuspend" -fsS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  >"${ARTIFACTS_DIR}/unsuspend-client.json" \
  || fail "unsuspend client endpoint failed" "control-plane" "./scripts/dev/unsuspend-client.sh ${DEMO_CLIENT_ID}"
curl_base_url "${BASE_URL}/v1/models" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  >"${ARTIFACTS_DIR}/models-after-unsuspend.json" \
  || fail "unsuspended client could not access models endpoint" "control-plane" "cat ${ARTIFACTS_DIR}/unsuspend-client.json"

log "testing client portal"
curl_base_url "${BASE_URL}/client-portal" -fsS >"${ARTIFACTS_DIR}/client-portal.html" \
  || fail "client portal page failed" "control-plane" "curl ${BASE_URL}/client-portal"
if grep -q 'X-Admin-Token' "${ARTIFACTS_DIR}/client-portal.html"; then
  fail "client portal exposed admin token semantics" "control-plane" "cat ${ARTIFACTS_DIR}/client-portal.html"
fi
curl_base_url "${BASE_URL}/portal/me" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  >"${ARTIFACTS_DIR}/portal-me.json" \
  || fail "portal me failed" "control-plane" "curl -H 'Authorization: Bearer ...' ${BASE_URL}/portal/me"
curl_base_url "${BASE_URL}/portal/usage" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  >"${ARTIFACTS_DIR}/portal-usage.json" \
  || fail "portal usage failed" "control-plane" "curl -H 'Authorization: Bearer ...' ${BASE_URL}/portal/usage"
curl_base_url "${BASE_URL}/portal/invoices" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  >"${ARTIFACTS_DIR}/portal-invoices.json" \
  || fail "portal invoices failed" "control-plane" "curl -H 'Authorization: Bearer ...' ${BASE_URL}/portal/invoices"
curl_base_url "${BASE_URL}/portal/test-chat" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Responda em uma frase curta: o portal está funcional?"}' \
  >"${ARTIFACTS_DIR}/portal-test-chat.json" \
  || fail "portal test chat failed" "control-plane" "curl -H 'Authorization: Bearer ...' ${BASE_URL}/portal/test-chat"

dc ps >"${ARTIFACTS_DIR}/compose-ps.txt" 2>&1 || true

log "running router presence test"
.venv/bin/pytest tests/test_router_presence.py -v >"${ARTIFACTS_DIR}/test-router-presence.log" 2>&1 || fail "router presence test failed" "" "cat ${ARTIFACTS_DIR}/test-router-presence.log"

printf '\n[validate][summary] success\n'
printf '[validate][summary] artifacts=%s\n' "${ARTIFACTS_DIR}"
printf '[validate][summary] endpoint=%s/v1/chat/completions\n' "${BASE_URL}"

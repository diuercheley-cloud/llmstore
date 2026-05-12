#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT_DIR}/scripts/common.sh"
# shellcheck source=/dev/null
source "${ROOT_DIR}/lib/validation-logging.sh"

init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ARTIFACTS_DIR="${ROOT_DIR}/artifacts/validate-observability-local/$(date +%Y%m%dT%H%M%S)"
mkdir -p "${ARTIFACTS_DIR}"

log_section "Observability Validation"

log() {
  log_info "$*"
}

fail() {
  log_error "$*"
  exit 1
}

log "using base url ${BASE_URL}"

ADMIN_TOKEN="${ADMIN_TOKEN:-}"
[[ -n "${ADMIN_TOKEN}" ]] || fail "ADMIN_TOKEN is required"

log "discovering active model"
MODELS_JSON="$(curl_base_url "${BASE_URL}/admin/models" -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}")" || fail "failed to load admin models"
MODEL_ID="$(printf '%s' "${MODELS_JSON}" | python3 -c 'import json,sys
data=json.load(sys.stdin)
registry=data.get("registry") or []
if not registry:
    raise SystemExit(1)
chosen=next((item for item in registry if item.get("is_active")), registry[0])
print(chosen["model_id"])
')" || fail "no active model found"
log "selected model ${MODEL_ID}"

log "issuing demo api key"
API_KEY="$(issue_demo_api_key "${BASE_URL}" "observability-validation")" || fail "failed to issue demo api key"

log "sending test inference request"
curl_base_url "${BASE_URL}/v1/chat/completions" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL_ID}\",\"messages\":[{\"role\":\"user\",\"content\":\"Responda com uma frase curta sobre observabilidade local.\"}],\"max_tokens\":32,\"stream\":false}" \
  >"${ARTIFACTS_DIR}/test-chat.json" || fail "test inference request failed"

log "scraping metrics"
curl_base_url "${BASE_URL}/metrics" -fsS >"${ARTIFACTS_DIR}/metrics.txt" || fail "/metrics failed"

for metric in \
  "requests_total" \
  "request_latency_seconds" \
  "tokens_prompt_total" \
  "tokens_completion_total" \
  "tokens_total" \
  "inference_latency_seconds" \
  "queue_wait_seconds" \
  "cache_hits_total" \
  "cache_misses_total" \
  "backend_errors_total" \
  "model_errors_total"
do
  grep -q "${metric}" "${ARTIFACTS_DIR}/metrics.txt" || fail "missing metric ${metric}"
done

grep -q "X-Admin-Token" "${ARTIFACTS_DIR}/metrics.txt" && fail "admin token leaked into metrics"
grep -Fq "${ADMIN_TOKEN}" "${ARTIFACTS_DIR}/metrics.txt" && fail "admin secret leaked into metrics"
grep -Fq "${API_KEY}" "${ARTIFACTS_DIR}/metrics.txt" && fail "api key leaked into metrics"
grep -Fq "sk-local-" "${ARTIFACTS_DIR}/metrics.txt" && fail "local secret-like string leaked into metrics"

log "validating usage endpoints"
curl_base_url "${BASE_URL}/admin/usage/summary" -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" >"${ARTIFACTS_DIR}/usage-summary.json" || fail "usage summary failed"
curl_base_url "${BASE_URL}/admin/usage/by-client" -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" >"${ARTIFACTS_DIR}/usage-by-client.json" || fail "usage by-client failed"
curl_base_url "${BASE_URL}/admin/usage/by-model" -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" >"${ARTIFACTS_DIR}/usage-by-model.json" || fail "usage by-model failed"

python3 - <<'PY' "${ARTIFACTS_DIR}/usage-summary.json" "${ARTIFACTS_DIR}/usage-by-client.json" "${ARTIFACTS_DIR}/usage-by-model.json"
import json
import sys

summary = json.load(open(sys.argv[1], encoding="utf-8"))
by_client = json.load(open(sys.argv[2], encoding="utf-8"))
by_model = json.load(open(sys.argv[3], encoding="utf-8"))

assert "summary" in summary
assert "clients" in summary
assert "models" in summary
assert isinstance(by_client, list)
assert isinstance(by_model, list)
assert "requests_today" in summary["summary"]
assert "tokens_month" in summary["summary"]
PY

log "validating dashboard endpoint"
curl_base_url "${BASE_URL}/admin-dashboard" -fsS >"${ARTIFACTS_DIR}/admin-dashboard.html" || fail "admin dashboard failed"

log "SUCCESS: observability validation completed"

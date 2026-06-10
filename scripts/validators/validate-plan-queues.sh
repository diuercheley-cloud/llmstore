#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
# shellcheck source=/dev/null
source "${ROOT_DIR}/scripts/dev/lib/validation-logging.sh"

init_stack_env

ARTIFACTS_DIR="${ROOT_DIR}/artifacts/validate-plan-queues/$(date +%Y%m%dT%H%M%S)"
mkdir -p "${ARTIFACTS_DIR}"
BASE_URL="${BASE_URL:-$(default_base_url)}"

log_section "Plan Queues Validation"

log() {
  log_info "$*"
}

log "Step 1: Get plan IDs"
PLANS_JSON=$(curl_base_url "${BASE_URL}/admin/billing/plans" -sS -H "X-Admin-Token: ${ADMIN_TOKEN}")
log_curl_mode "${BASE_URL}/admin/billing/plans"
FREE_PLAN_ID=$(echo "${PLANS_JSON}" | jq -r '.[] | select(.code=="free") | .id')
PRO_PLAN_ID=$(echo "${PLANS_JSON}" | jq -r '.[] | select(.code=="pro") | .id')

# Ensure rate limits are high enough for testing
curl_base_url "${BASE_URL}/admin/billing/plans/${FREE_PLAN_ID}" -sS -X PATCH \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
  -d '{"rate_limit_per_minute": 1000}' > /dev/null
log_curl_mode "${BASE_URL}/admin/billing/plans/${FREE_PLAN_ID}"

log "Step 2: Create test clients"
create_client_on_plan() {
    local name=$1
    local plan_id=$2
    local is_admin=$3
    
    local client_data='{"name": "'"${name}"'", "billing_plan_id": "'"${plan_id}"'"}'
    if [ "${is_admin}" == "true" ]; then
        client_data='{"name": "'"${name}"'", "billing_plan_id": "'"${plan_id}"'", "metadata_json": "{\"is_admin\": true}"}'
    fi
    
    local client_resp=$(curl_base_url "${BASE_URL}/admin/clients" -sS -X POST \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "${client_data}")
    
    local client_id=$(echo "${client_resp}" | jq -r '.id')
    local api_key=$(curl_base_url "${BASE_URL}/admin/api-keys" -sS -X POST \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"name\": \"val-key\", \"client_id\": \"${client_id}\"}" | jq -r '.api_key')
    
    echo "${api_key}"
}

KEY_FREE=$(create_client_on_plan "val-free-$(date +%s)" "${FREE_PLAN_ID}" "false")
KEY_ADMIN=$(create_client_on_plan "val-admin-$(date +%s)" "${PRO_PLAN_ID}" "true")

log "Step 3: Validate queue-aware request paths"
for label in FREE ADMIN; do
  if [[ "${label}" == "FREE" ]]; then
    api_key="${KEY_FREE}"
  else
    api_key="${KEY_ADMIN}"
  fi

  status_code="$(curl_base_url "${BASE_URL}/v1/chat/completions" -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${api_key}" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"unsloth/gemma-4-E4B-it-GGUF\",\"messages\":[{\"role\":\"user\",\"content\":\"queue validation ${label}\"}],\"max_tokens\":12}")"
  log_curl_mode "${BASE_URL}/v1/chat/completions"
  echo "RESULT: ${label} | Status: ${status_code}" | tee -a "${ARTIFACTS_DIR}/results.log"
  if [[ "${status_code}" != "200" && "${status_code}" != "202" ]]; then
    log_error "unexpected chat status for ${label}: ${status_code}"
    exit 1
  fi
done

log "Step 4: Check metrics"
curl_base_url "${BASE_URL}/metrics" -sS | grep -E "control_plane_queue_" || true
log_curl_mode "${BASE_URL}/metrics"

log "Step 5: Check Admin Status API"
curl_base_url "${BASE_URL}/admin/status" -sS -H "X-Admin-Token: ${ADMIN_TOKEN}" | jq '.inference_queues'
log_curl_mode "${BASE_URL}/admin/status"

log "SUCCESS: Plan-based queues validation completed."

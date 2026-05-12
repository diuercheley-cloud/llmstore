#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
# shellcheck source=/dev/null
source "${ROOT_DIR}/scripts/lib/validation-logging.sh"

init_stack_env

ARTIFACTS_DIR="${ROOT_DIR}/artifacts/validate-routing/$(date +%Y%m%dT%H%M%S)"
mkdir -p "${ARTIFACTS_DIR}"
BASE_URL="${BASE_URL:-$(default_base_url)}"

log_section "Routing Validation"

log() {
  log_info "$*"
}

fail() {
  log_error "$*"
  exit 1
}

log "Step 1: Create a test plan with a routing policy"
PLAN_CODE="val-routing-premium"
PLAN_DATA='{
  "code": "'"${PLAN_CODE}"'",
  "name": "Validation Routing Plan",
  "rate_limit_per_minute": 60,
  "daily_token_quota": 1000000,
  "weekly_token_quota": 5000000,
  "monthly_token_quota": 20000000,
  "max_output_tokens": 4096,
  "allowed_models": ["unsloth/gemma-4-E4B-it-GGUF", "alias-model"],
  "routing_policy": {
    "rules": [
      {"action": "prioritize_backend_type", "value": "vllm", "priority_boost": 50}
    ]
  }
}'

# Create or update plan
curl_base_url "${BASE_URL}/admin/billing/plans" -sS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "${PLAN_DATA}" > "${ARTIFACTS_DIR}/plan.json" || true
log_curl_mode "${BASE_URL}/admin/billing/plans"

PLAN_ID=$(jq -r '.id' "${ARTIFACTS_DIR}/plan.json" 2>/dev/null || true)
if [[ "${PLAN_ID}" == "null" || -z "${PLAN_ID}" ]]; then
    # Maybe it already exists, try to find it
    PLAN_ID=$(curl_base_url "${BASE_URL}/admin/billing/plans" -sS -H "X-Admin-Token: ${ADMIN_TOKEN}" | jq -r '.[] | select(.code=="'"${PLAN_CODE}"'") | .id')
    log_curl_mode "${BASE_URL}/admin/billing/plans"
    # Update it
    curl_base_url "${BASE_URL}/admin/billing/plans/${PLAN_ID}" -sS -X PATCH \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "${PLAN_DATA}" > "${ARTIFACTS_DIR}/plan_updated.json"
    log_curl_mode "${BASE_URL}/admin/billing/plans/${PLAN_ID}"
fi

log "Step 2: Create a test client on this plan"
CLIENT_NAME="val-routing-client-$(date +%s)"
CLIENT_DATA='{
  "name": "'"${CLIENT_NAME}"'",
  "billing_plan_id": "'"${PLAN_ID}"'",
  "allowed_models": ["unsloth/gemma-4-E4B-it-GGUF", "alias-model"]
}'

curl_base_url "${BASE_URL}/admin/clients" -sS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "${CLIENT_DATA}" > "${ARTIFACTS_DIR}/client.json"
log_curl_mode "${BASE_URL}/admin/clients"

CLIENT_ID=$(jq -r '.id' "${ARTIFACTS_DIR}/client.json")
API_KEY=$(curl_base_url "${BASE_URL}/admin/api-keys" -sS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"name": "routing-val-key", "client_id": "'"${CLIENT_ID}"'"}' | jq -r '.api_key')
log_curl_mode "${BASE_URL}/admin/api-keys"

log "Step 3: Test routing explanation"
curl_base_url "${BASE_URL}/admin/routing/explain" -sS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "client_id": "'"${CLIENT_ID}"'"
  }' > "${ARTIFACTS_DIR}/explain.json"
log_curl_mode "${BASE_URL}/admin/routing/explain"

log "Routing explanation check:"
jq '.' "${ARTIFACTS_DIR}/explain.json"

log "Step 4: Test unauthorized model rewrite to default"
# nemotron exists but is NOT in the allowed list for this plan
curl_base_url "${BASE_URL}/admin/routing/explain" -sS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvidia/nemotron-3-nano-4b",
    "client_id": "'"${CLIENT_ID}"'"
  }' > "${ARTIFACTS_DIR}/explain_rewrite.json"

log "Rewrite check (should resolve to default model):"
RESOLVED_MODEL=$(jq -r '.resolved_model_id' "${ARTIFACTS_DIR}/explain_rewrite.json")
log "Resolved model for forbidden request: ${RESOLVED_MODEL}"
log_curl_mode "${BASE_URL}/admin/routing/explain"

log "Step 5: Cleanup test client"
curl_base_url "${BASE_URL}/admin/clients/${CLIENT_ID}" -sS -X DELETE \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" > /dev/null || true
log_curl_mode "${BASE_URL}/admin/clients/${CLIENT_ID}"

log "SUCCESS: Routing validation completed."
log "Artifacts in ${ARTIFACTS_DIR}"

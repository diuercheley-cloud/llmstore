#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"

init_stack_env
BASE_URL="${BASE_URL:-http://localhost:18080}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

log() {
  printf '[runtime-health] %s\n' "$*"
}

fail() {
  printf '[runtime-health][error] %s\n' "$*" >&2
  exit 1
}

check_jq() {
    if ! command -v jq &> /dev/null; then
        fail "jq is required but not installed."
    fi
}

check_jq

log "Validating /health..."
HEALTH_RESP=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health")
if [[ "$HEALTH_RESP" != "200" ]]; then
    fail "/health returned $HEALTH_RESP, expected 200"
fi

log "Validating /ready..."
READY_FILE=$(mktemp)
READY_CODE=$(curl -s -o "$READY_FILE" -w "%{http_code}" "${BASE_URL}/ready")
if [[ "$READY_CODE" != "200" && "$READY_CODE" != "503" ]]; then
    fail "/ready returned $READY_CODE, expected 200 or 503"
fi
jq . "$READY_FILE" > /dev/null || fail "/ready returned invalid JSON"
rm "$READY_FILE"

log "Validating /status sanitization..."
STATUS_FILE=$(mktemp)
curl -s -o "$STATUS_FILE" "${BASE_URL}/status"
if grep -qiE "ADMIN_TOKEN|DATABASE_URL|REDIS_URL|API_KEY|sk-" "$STATUS_FILE"; then
    fail "/status contains sensitive information"
fi
rm "$STATUS_FILE"

log "Validating /admin/health/deep protection..."
DEEP_UNAUTH=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/admin/health/deep")
if [[ "$DEEP_UNAUTH" != "401" ]]; then
    fail "/admin/health/deep did not return 401 for unauthorized access"
fi

log "Validating /admin/health/deep content..."
DEEP_FILE=$(mktemp)
DEEP_CODE=$(curl -s -H "X-Admin-Token: ${ADMIN_TOKEN}" -o "$DEEP_FILE" -w "%{http_code}" "${BASE_URL}/admin/health/deep")
if [[ "$DEEP_CODE" != "200" ]]; then
    fail "/admin/health/deep returned $DEEP_CODE, expected 200"
fi

# Mandatory sections
for section in api postgres redis queues inference_backends models rag tts billing security readiness_score; do
    jq -e ".$section" "$DEEP_FILE" > /dev/null || fail "Section '$section' missing in /admin/health/deep response"
done

# Uptime check
UPTIME=$(jq .api.uptime_seconds "$DEEP_FILE")
if [[ "$UPTIME" == "null" || $(echo "$UPTIME <= 0" | bc -l) -eq 1 ]]; then
    fail "Invalid uptime_seconds: $UPTIME"
fi

# Sanitization check for deep health
if grep -qiE "ADMIN_TOKEN|DATABASE_URL|REDIS_URL|API_KEY|sk-" "$DEEP_FILE" | grep -v "check_secrets_available"; then
    # We allow check_secrets_available key itself
    if ! jq . "$DEEP_FILE" | grep -qiE "ADMIN_TOKEN|DATABASE_URL|REDIS_URL|API_KEY|sk-"; then
        log "Deep health content seems safe (grep matched but jq filtered doesn't show secrets)"
    else
        fail "/admin/health/deep contains sensitive information"
    fi
fi

# Verify specific fields
READINESS=$(jq -r .readiness_score "$DEEP_FILE")
log "Readiness score: $READINESS"
if [[ "$READINESS" != "READY" && "$READINESS" != "DEGRADED" && "$READINESS" != "NOT_READY" ]]; then
    fail "Invalid readiness_score: $READINESS"
fi

rm "$DEEP_FILE"

log "Validation successful!"

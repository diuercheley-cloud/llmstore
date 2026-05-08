#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/validation-logging.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

if [[ -z "${ADMIN_TOKEN}" ]]; then
  log_error "ADMIN_TOKEN must be set"
  exit 1
fi

log_section "API Keys Validation"

log() {
  log_info "$*"
}

# 1. Create client
log "Creating client..."
CLIENT_NAME="api-key-test-$(date +%s)"
CLIENT_ID=$(curl_base_url "${BASE_URL}/admin/clients" -fsS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"${CLIENT_NAME}\", \"rate_limit_per_minute\": 60}" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
log_curl_mode "${BASE_URL}/admin/clients"
log "Client created: ${CLIENT_ID}"

# 2. Create API key
log "Creating API key..."
KEY_NAME="key-1"
KEY_DATA=$(curl_base_url "${BASE_URL}/admin/api-keys" -fsS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"${CLIENT_ID}\", \"name\":\"${KEY_NAME}\"}")
log_curl_mode "${BASE_URL}/admin/api-keys"
API_KEY=$(echo "${KEY_DATA}" | python3 -c "import sys, json; print(json.load(sys.stdin)['api_key'])")
KEY_ID=$(echo "${KEY_DATA}" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
log "API key created: ${API_KEY} (ID: ${KEY_ID})"

# 3. Use API key
log "Using API key in /v1/chat/completions..."
curl_base_url "${BASE_URL}/v1/chat/completions" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Hi"}],
    "max_tokens": 5
  }' > /dev/null
log_curl_mode "${BASE_URL}/v1/chat/completions"
log "API key used successfully"

# 4. Check last_used_at
log "Checking last_used_at..."
LAST_USED=$(curl_base_url "${BASE_URL}/admin/api-keys" -fsS \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -c "import sys, json; keys = json.load(sys.stdin); key = next(k for k in keys if k['id'] == '${KEY_ID}'); print(key['last_used_at'])")
log_curl_mode "${BASE_URL}/admin/api-keys"
if [[ "${LAST_USED}" == "null" ]]; then
  log "Error: last_used_at is null"
  exit 1
fi
log "last_used_at is: ${LAST_USED}"

# 5. Revoke API key
log "Revoking API key..."
curl_base_url "${BASE_URL}/admin/api-keys/${KEY_ID}" -fsS -X DELETE \
  -H "X-Admin-Token: ${ADMIN_TOKEN}"
log_curl_mode "${BASE_URL}/admin/api-keys/${KEY_ID}"
log "API key revoked"

# 6. Confirm revoked key receives 401
log "Testing revoked key (should receive 401)..."
STATUS=$(curl_base_url "${BASE_URL}/v1/chat/completions" -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model": "unsloth/gemma-4-E4B-it-GGUF", "messages": [{"role": "user", "content": "Hi"}]}')
log_curl_mode "${BASE_URL}/v1/chat/completions"
if [[ "${STATUS}" != "401" ]]; then
  log "Error: Expected 401, got ${STATUS}"
  exit 1
fi
log "Received expected 401"

# 7. Create expired key and confirm 401
log "Creating expired key..."
EXPIRES_AT=$(date -u -d "1 minute ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v-1M +"%Y-%m-%dT%H:%M:%SZ")
EXPIRED_KEY_DATA=$(curl_base_url "${BASE_URL}/admin/api-keys" -fsS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"${CLIENT_ID}\", \"name\":\"expired-key\", \"expires_at\":\"${EXPIRES_AT}\"}")
log_curl_mode "${BASE_URL}/admin/api-keys"
EXPIRED_API_KEY=$(echo "${EXPIRED_KEY_DATA}" | python3 -c "import sys, json; print(json.load(sys.stdin)['api_key'])")
log "Expired key created: ${EXPIRED_API_KEY}"

log "Testing expired key (should receive 401)..."
STATUS=$(curl_base_url "${BASE_URL}/v1/chat/completions" -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${EXPIRED_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model": "unsloth/gemma-4-E4B-it-GGUF", "messages": [{"role": "user", "content": "Hi"}]}')
log_curl_mode "${BASE_URL}/v1/chat/completions"
if [[ "${STATUS}" != "401" ]]; then
  log "Error: Expected 401, got ${STATUS}"
  exit 1
fi
log "Received expected 401 for expired key"

# 8. Test allowed_ips
log "Creating key with allowed_ips..."
IP_KEY_DATA=$(curl_base_url "${BASE_URL}/admin/api-keys" -fsS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"${CLIENT_ID}\", \"name\":\"ip-restricted-key\", \"allowed_ips\":[\"1.2.3.4\"]}")
log_curl_mode "${BASE_URL}/admin/api-keys"
IP_API_KEY=$(echo "${IP_KEY_DATA}" | python3 -c "import sys, json; print(json.load(sys.stdin)['api_key'])")
log "IP restricted key created: ${IP_API_KEY} (allowed: 1.2.3.4)"

log "Testing IP restricted key (should receive 403)..."
STATUS=$(curl_base_url "${BASE_URL}/v1/chat/completions" -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${IP_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model": "unsloth/gemma-4-E4B-it-GGUF", "messages": [{"role": "user", "content": "Hi"}]}')
log_curl_mode "${BASE_URL}/v1/chat/completions"
if [[ "${STATUS}" != "403" ]]; then
  log "Error: Expected 403, got ${STATUS}"
  exit 1
fi
log "Received expected 403 for IP restricted key"

log "Validation successful!"

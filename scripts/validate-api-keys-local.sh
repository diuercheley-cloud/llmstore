#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

if [[ -z "${ADMIN_TOKEN}" ]]; then
  echo "Error: ADMIN_TOKEN must be set (e.g. export ADMIN_TOKEN=...)"
  exit 1
fi

log() {
  printf '[validate-api-keys] %s\n' "$*"
}

# 1. Create client
log "Creating client..."
CLIENT_NAME="api-key-test-$(date +%s)"
CLIENT_ID=$(curl -fsS -X POST "${BASE_URL}/admin/clients" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"${CLIENT_NAME}\", \"rate_limit_per_minute\": 60}" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
log "Client created: ${CLIENT_ID}"

# 2. Create API key
log "Creating API key..."
KEY_NAME="key-1"
KEY_DATA=$(curl -fsS -X POST "${BASE_URL}/admin/api-keys" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"${CLIENT_ID}\", \"name\":\"${KEY_NAME}\"}")
API_KEY=$(echo "${KEY_DATA}" | python3 -c "import sys, json; print(json.load(sys.stdin)['api_key'])")
KEY_ID=$(echo "${KEY_DATA}" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
log "API key created: ${API_KEY} (ID: ${KEY_ID})"

# 3. Use API key
log "Using API key in /v1/chat/completions..."
curl -fsS "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "unsloth/gemma-4-E4B-it-GGUF",
    "messages": [{"role": "user", "content": "Hi"}],
    "max_tokens": 5
  }' > /dev/null
log "API key used successfully"

# 4. Check last_used_at
log "Checking last_used_at..."
LAST_USED=$(curl -fsS "${BASE_URL}/admin/api-keys" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -c "import sys, json; keys = json.load(sys.stdin); key = next(k for k in keys if k['id'] == '${KEY_ID}'); print(key['last_used_at'])")
if [[ "${LAST_USED}" == "null" ]]; then
  log "Error: last_used_at is null"
  exit 1
fi
log "last_used_at is: ${LAST_USED}"

# 5. Revoke API key
log "Revoking API key..."
curl -fsS -X DELETE "${BASE_URL}/admin/api-keys/${KEY_ID}" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}"
log "API key revoked"

# 6. Confirm revoked key receives 401
log "Testing revoked key (should receive 401)..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model": "unsloth/gemma-4-E4B-it-GGUF", "messages": [{"role": "user", "content": "Hi"}]}')
if [[ "${STATUS}" != "401" ]]; then
  log "Error: Expected 401, got ${STATUS}"
  exit 1
fi
log "Received expected 401"

# 7. Create expired key and confirm 401
log "Creating expired key..."
EXPIRES_AT=$(date -u -d "1 minute ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -v-1M +"%Y-%m-%dT%H:%M:%SZ")
EXPIRED_KEY_DATA=$(curl -fsS -X POST "${BASE_URL}/admin/api-keys" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"${CLIENT_ID}\", \"name\":\"expired-key\", \"expires_at\":\"${EXPIRES_AT}\"}")
EXPIRED_API_KEY=$(echo "${EXPIRED_KEY_DATA}" | python3 -c "import sys, json; print(json.load(sys.stdin)['api_key'])")
log "Expired key created: ${EXPIRED_API_KEY}"

log "Testing expired key (should receive 401)..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${EXPIRED_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model": "unsloth/gemma-4-E4B-it-GGUF", "messages": [{"role": "user", "content": "Hi"}]}')
if [[ "${STATUS}" != "401" ]]; then
  log "Error: Expected 401, got ${STATUS}"
  exit 1
fi
log "Received expected 401 for expired key"

# 8. Test allowed_ips
log "Creating key with allowed_ips..."
IP_KEY_DATA=$(curl -fsS -X POST "${BASE_URL}/admin/api-keys" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"${CLIENT_ID}\", \"name\":\"ip-restricted-key\", \"allowed_ips\":[\"1.2.3.4\"]}")
IP_API_KEY=$(echo "${IP_KEY_DATA}" | python3 -c "import sys, json; print(json.load(sys.stdin)['api_key'])")
log "IP restricted key created: ${IP_API_KEY} (allowed: 1.2.3.4)"

log "Testing IP restricted key (should receive 403)..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${IP_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model": "unsloth/gemma-4-E4B-it-GGUF", "messages": [{"role": "user", "content": "Hi"}]}')
if [[ "${STATUS}" != "403" ]]; then
  log "Error: Expected 403, got ${STATUS}"
  exit 1
fi
log "Received expected 403 for IP restricted key"

log "Validation successful!"

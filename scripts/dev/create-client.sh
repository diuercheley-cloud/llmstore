#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in .env or environment}"
CLIENT_NAME="${1:?usage: ./scripts/dev/create-client.sh CLIENT_NAME [DESCRIPTION]}"
CLIENT_DESCRIPTION="${2:-client created by script}"
RATE_LIMIT_PER_MINUTE="${RATE_LIMIT_PER_MINUTE:-5}"
DAILY_TOKEN_QUOTA="${DAILY_TOKEN_QUOTA:-20000}"
MONTHLY_TOKEN_QUOTA="${MONTHLY_TOKEN_QUOTA:-300000}"
MAX_CONTEXT_TOKENS="${MAX_CONTEXT_TOKENS:-32768}"
MAX_OUTPUT_TOKENS="${MAX_OUTPUT_TOKENS:-32768}"

client_json="$(
  curl_base_url "${BASE_URL}/admin/clients" -fsS \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"${CLIENT_NAME}\",
      \"description\": \"${CLIENT_DESCRIPTION}\",
      \"rate_limit_per_minute\": ${RATE_LIMIT_PER_MINUTE},
      \"daily_token_quota\": ${DAILY_TOKEN_QUOTA},
      \"monthly_token_quota\": ${MONTHLY_TOKEN_QUOTA},
      \"max_context_tokens\": ${MAX_CONTEXT_TOKENS},
      \"max_output_tokens\": ${MAX_OUTPUT_TOKENS}
    }"
)"

client_id="$(printf '%s' "${client_json}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')"

key_json="$(
  curl_base_url "${BASE_URL}/admin/api-keys" -fsS \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"client_id\":\"${client_id}\",\"name\":\"${CLIENT_NAME}-default\"}"
)"

printf '%s\n' "${key_json}" | python3 -c '
import json, sys
data = json.load(sys.stdin)
print("client_id=" + str(data["client_id"]))
print("api_key=" + str(data["api_key"]))
print("key_prefix=" + str(data["key_prefix"]))
'

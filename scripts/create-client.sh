#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in .env or environment}"
CLIENT_NAME="${1:?usage: ./scripts/create-client.sh CLIENT_NAME [DESCRIPTION]}"
CLIENT_DESCRIPTION="${2:-client created by script}"
RATE_LIMIT_PER_MINUTE="${RATE_LIMIT_PER_MINUTE:-5}"
DAILY_TOKEN_QUOTA="${DAILY_TOKEN_QUOTA:-20000}"
MONTHLY_TOKEN_QUOTA="${MONTHLY_TOKEN_QUOTA:-300000}"
MAX_CONTEXT_TOKENS="${MAX_CONTEXT_TOKENS:-2048}"
MAX_OUTPUT_TOKENS="${MAX_OUTPUT_TOKENS:-1024}"

client_json="$(
  curl -fsS "${BASE_URL}/admin/clients" \
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
  curl -fsS "${BASE_URL}/admin/api-keys" \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"client_id\":\"${client_id}\",\"name\":\"${CLIENT_NAME}-default\"}"
)"

printf '%s\n' "${key_json}" | python3 -c '
import json, sys
data = json.load(sys.stdin)
print(f"client_id={data['client_id']}")
print(f"api_key={data['api_key']}")
print(f"key_prefix={data['key_prefix']}")
'

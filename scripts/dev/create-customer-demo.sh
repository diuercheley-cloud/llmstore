#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
CLIENT_NAME="${1:-customer-demo}"
CLIENT_DESCRIPTION="${2:-cliente demo para onboarding comercial}"
PLAN_CODE="${3:-basic}"

client_output="$("${SCRIPT_DIR}/create-client.sh" "${CLIENT_NAME}" "${CLIENT_DESCRIPTION}")"
CLIENT_ID="$(printf '%s\n' "${client_output}" | awk -F= '/^client_id=/{print $2}' | tail -n1)"
API_KEY="$(printf '%s\n' "${client_output}" | awk -F= '/^api_key=/{print $2}' | tail -n1)"

if [[ -n "${CLIENT_ID}" && -n "${PLAN_CODE}" ]]; then
  "${SCRIPT_DIR}/set-client-plan.sh" "${CLIENT_ID}" "${PLAN_CODE}" >/dev/null
fi

printf 'client_id=%s\n' "${CLIENT_ID}"
printf 'plan_code=%s\n' "${PLAN_CODE}"
printf 'api_key=%s\n' "${API_KEY}"
printf 'client_portal_url=%s/client-portal\n' "${BASE_URL}"
printf 'chat_endpoint=%s/v1/chat/completions\n' "${BASE_URL}"

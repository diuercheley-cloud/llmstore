#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
API_KEY="$(issue_demo_api_key "${BASE_URL}" "opencode-test")"

printf '[test] sending OpenCode-style request\n'

response="$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
  "model": "gemma",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "oi"},
        {"type": "text", "text": "<system-reminder>teste</system-reminder>"}
      ]
    }
  ],
  "max_tokens": 32000,
  "stream": false
}')"

body=$(echo "$response" | head -n -1)
status=$(echo "$response" | tail -n 1)

if [[ "${status}" -ne 200 ]]; then
  printf '[error] request failed with status %s\n' "${status}"
  echo "${body}"
  exit 1
fi

printf '[success] request succeeded with status 200\n'
echo "${body}" | python3 -m json.tool

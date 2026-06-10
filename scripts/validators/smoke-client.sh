#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
API_KEY="${API_KEY:-${1:-}}"
API_KEY="${API_KEY:?usage: API_KEY=... ./scripts/validators/smoke-client.sh or ./scripts/validators/smoke-client.sh API_KEY}"
MODEL="${MODEL:-${MODEL_ID:-unsloth/gemma-4-E4B-it-GGUF}}"

printf '[smoke] models\n'
curl -fsS "${BASE_URL}/v1/models" \
  -H "Authorization: Bearer ${API_KEY}" | python3 -m json.tool

printf '\n[smoke] chat\n'
curl -fsS "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [{\"role\": \"user\", \"content\": \"Responda apenas com OK.\"}],
    \"max_tokens\": 32,
    \"stream\": false,
    \"include_reasoning\": false
  }" | python3 -m json.tool

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env
BASE_URL="${BASE_URL:-$(default_base_url)}"
API_KEY="$(require_api_key "${BASE_URL}" "test-chat")"
API_KEY="${API_KEY:?set API_KEY or configure ADMIN_TOKEN to mint a demo key}"
MODEL="${MODEL:-${MODEL_ID:-unsloth/gemma-4-E4B-it-GGUF}}"

curl -fsS "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [{\"role\": \"user\", \"content\": \"Responda em uma frase: o que e WSL2?\"}],
    \"max_tokens\": 128,
    \"stream\": false,
    \"include_reasoning\": false
  }" | python3 -m json.tool

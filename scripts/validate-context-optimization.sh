#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env
BASE_URL="${BASE_URL:-$(default_base_url)}"

# Try to get or create a client/API key
if [[ -z "${API_KEY:-}" ]]; then
    API_KEY=$(./scripts/create-client.sh "context-test-client" | grep "API Key:" | awk '{print $3}')
fi

MODEL="${MODEL:-unsloth/gemma-4-E4B-it-GGUF}"

echo "--- Testing Context Optimization ---"
echo "Sending request with 'oi' to trigger Simple Input Mode..."

curl -s -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [
      {\"role\": \"system\", \"content\": \"You are a JS expert.\"},
      {\"role\": \"user\", \"content\": \"This is a long message 1\"},
      {\"role\": \"assistant\", \"content\": \"Ok\"},
      {\"role\": \"user\", \"content\": \"oi\"}
    ],
    \"max_tokens\": 32000,
    \"stream\": false
  }" > context_test_res.json

echo "Response stored in context_test_res.json"
cat context_test_res.json | python3 -m json.tool | grep -E "content|prompt_tokens" || true

echo "--- Checking logs for Simple Input Mode ---"
if [ -f "logs/control-plane.log" ]; then
    tail -n 50 logs/control-plane.log | grep "simple_input_mode\": true" | tail -n 1
else
    echo "Logs file not found in logs/control-plane.log, please check stdout of control-plane."
fi

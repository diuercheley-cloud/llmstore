#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env
BASE_URL="${BASE_URL:-$(default_base_url)}"
API_KEY="${API_KEY:?set API_KEY}"
MODEL="${MODEL:-${MODEL_ID:-unsloth/gemma-4-E4B-it-GGUF}}"
CONCURRENCY="${CONCURRENCY:-2}"
REQUESTS="${REQUESTS:-4}"

for i in $(seq 1 "${REQUESTS}"); do
  (
    curl -sS "${BASE_URL}/v1/chat/completions" \
      -H "Authorization: Bearer ${API_KEY}" \
      -H "Content-Type: application/json" \
      -d "{
        \"model\": \"${MODEL}\",
        \"messages\": [{\"role\": \"user\", \"content\": \"Resuma em uma frase o teste ${i}.\"}],
        \"max_tokens\": 64,
        \"stream\": false
      }" >/dev/null
    echo "request ${i} ok"
  ) &

  while [[ "$(jobs -r | wc -l)" -ge "${CONCURRENCY}" ]]; do
    sleep 0.5
  done
done

wait

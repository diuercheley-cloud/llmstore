#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"

init_stack_env

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="${ROOT_DIR}/artifacts/quality/${TIMESTAMP}"
mkdir -p "${OUTPUT_DIR}"

BASE_URL="${BASE_URL:-$(default_base_url)}"
API_KEY="${API_KEY:-$(issue_demo_api_key "${BASE_URL}")}"

echo "--- Iniciando Quality Smoke Test (Release 0.5.0-local) ---"
echo "Resultados em: ${OUTPUT_DIR}"

test_request() {
  local name=$1
  local payload=$2
  echo "Testing: $name..."
  curl -s -X POST "${BASE_URL}/v1/chat/completions" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$payload" > "${OUTPUT_DIR}/${name}.json"
  echo "Done $name."
}

# 1. Resposta curta
test_request "short_response" '{
  "model": "unsloth/gemma-4-E4B-it-GGUF",
  "messages": [{"role": "user", "content": "Diga oi em uma palavra."}],
  "max_tokens": 10
}'

# 2. Resposta técnica
test_request "technical_response" '{
  "model": "unsloth/gemma-4-E4B-it-GGUF",
  "messages": [{"role": "user", "content": "Como funciona o algoritmo Attention em Transformers?"}],
  "max_tokens": 128
}'

# 3. Resposta em português
test_request "portuguese_response" '{
  "model": "unsloth/gemma-4-E4B-it-GGUF",
  "messages": [{"role": "user", "content": "Quais as principais cidades do Brasil?"}],
  "max_tokens": 128
}'

# 4. Streaming sem reasoning
echo "Testing: streaming_no_reasoning..."
curl -s -X POST "${BASE_URL}/v1/chat/completions" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "unsloth/gemma-4-E4B-it-GGUF",
      "messages": [{"role": "user", "content": "Conte uma piada curta."}],
      "stream": true,
      "include_reasoning": false
    }' > "${OUTPUT_DIR}/streaming_no_reasoning.txt"
echo "Done streaming_no_reasoning."

# 5. Safety Profile: Strict
test_request "safety_strict" '{
  "model": "unsloth/gemma-4-E4B-it-GGUF",
  "messages": [{"role": "user", "content": "Explique física quântica para uma criança."}],
  "safety_profile": "strict",
  "max_tokens": 128
}'

echo "Quality Smoke Test finalizado."

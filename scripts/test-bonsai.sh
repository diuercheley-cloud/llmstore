#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"

for _ in $(seq 1 30); do
  if curl_base_url "${BASE_URL}/ready" -fsS >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

curl_base_url "${BASE_URL}/ready" -fsS >/dev/null

if [[ "${BONSAI_ENABLED:-false}" != "true" ]]; then
  printf '[bonsai][skip] BONSAI_ENABLED=false no ambiente %s\n' "${STACK_ENV_FILE}" >&2
  exit 0
fi

if [[ ! -f "${ROOT_DIR}/models/${BONSAI_MODEL_FILE:-bonsai-8B.gguf}" ]]; then
  printf '[bonsai][error] arquivo ausente: %s/models/%s\n' "${ROOT_DIR}" "${BONSAI_MODEL_FILE:-bonsai-8B.gguf}" >&2
  printf '[bonsai][error] inicie com COMPOSE_PROFILES=bonsai e provisione o GGUF antes do teste\n' >&2
  exit 1
fi

API_KEY="$(require_api_key "${BASE_URL}" "test-bonsai")"
API_KEY="${API_KEY:?set API_KEY or configure ADMIN_TOKEN to mint a demo key}"
MODEL="${MODEL:-bonsai}"

printf '[bonsai] listando modelos ativos\n'
curl_base_url "${BASE_URL}/v1/models" -fsS \
  -H "Authorization: Bearer ${API_KEY}" | python3 -c '
import json, sys
payload = json.load(sys.stdin)
models = [item["id"] for item in payload.get("data", [])]
print(models)
if "bonsai" not in models:
    raise SystemExit("bonsai alias not exposed in /v1/models")
'

printf '[bonsai] executando chat no backend bonsai-local\n'
curl_base_url "${BASE_URL}/v1/chat/completions" -fsS \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [{\"role\": \"user\", \"content\": \"Responda com uma frase curta: qual backend voce esta usando?\"}],
    \"max_tokens\": 96,
    \"stream\": false
  }" | python3 -m json.tool

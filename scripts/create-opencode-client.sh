#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in .env or environment}"

CLIENT_NAME="opencode-local"
CLIENT_DESCRIPTION="Cliente otimizado para compatibilidade com OpenCode"
PLAN_CODE="opencode-tools"
PLAN_NAME="OpenCode Tools"

SYSTEM_PROMPT='Você é um assistente de programação prestativo e direto.
Responda diretamente à pergunta do usuário sem preâmbulos desnecessários.
NÃO repita a pergunta do usuário.
NÃO gere blocos de planejamento como "Goal", "Progress", "Done", "In Progress", "Next Steps" ou "Relevant Files", a menos que o usuário peça explicitamente por um relatório de progresso.
Mantenha suas respostas técnicas curtas e focadas na solução.
Se o usuário disser apenas saudações como "oi" ou "olá", responda de forma breve e educada.'

METADATA='{"temperature":0.2,"top_p":0.8,"max_tokens":32768}'

printf '[opencode] garantindo cliente %s...\n' "${CLIENT_NAME}"

existing_client_id="$(
  curl_base_url "${BASE_URL}/admin/clients" -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    | python3 -c "import json, sys; d=json.load(sys.stdin); print(next((c['id'] for c in d if c['name'] == '${CLIENT_NAME}'), ''))"
)"

existing_plan_id="$(
  curl_base_url "${BASE_URL}/admin/billing/plans" -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    | python3 -c "import json, sys; d=json.load(sys.stdin); print(next((p['id'] for p in d if p['code'] == '${PLAN_CODE}'), ''))"
)"

plan_create_payload="$(
  PLAN_CODE="${PLAN_CODE}" PLAN_NAME="${PLAN_NAME}" python3 - <<'PY'
import json
import os

print(json.dumps({
    "code": os.environ["PLAN_CODE"],
    "name": os.environ["PLAN_NAME"],
    "description": "Plano dedicado para OpenCode com tools habilitado",
    "rate_limit_per_minute": 60,
    "daily_token_quota": 500000,
    "weekly_token_quota": 2000000,
    "monthly_token_quota": 5000000,
    "max_output_tokens": 32768,
    "max_context_tokens": 32768,
    "allow_streaming": True,
    "responses_enabled": True,
    "tools_enabled": True,
    "embeddings_enabled": True,
    "is_active": True,
    "support_level": "Community",
}))
PY
)"

plan_patch_payload='{"allow_streaming":true,"responses_enabled":true,"tools_enabled":true,"embeddings_enabled":true,"is_active":true,"max_output_tokens":32768,"max_context_tokens":32768}'

if [[ -n "${existing_plan_id}" ]]; then
  printf '[opencode] plano já existe (ID: %s), atualizando...\n' "${existing_plan_id}"
  curl_base_url "${BASE_URL}/admin/billing/plans/${existing_plan_id}" -fsS -X PATCH \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${plan_patch_payload}" >/dev/null
  plan_id="${existing_plan_id}"
else
  printf '[opencode] criando plano %s...\n' "${PLAN_CODE}"
  plan_json="$(
    curl_base_url "${BASE_URL}/admin/billing/plans" -fsS \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "${plan_create_payload}"
  )"
  plan_id="$(printf '%s' "${plan_json}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')"
fi

client_create_payload="$(
  CLIENT_NAME="${CLIENT_NAME}" \
  CLIENT_DESCRIPTION="${CLIENT_DESCRIPTION}" \
  SYSTEM_PROMPT="${SYSTEM_PROMPT}" \
  METADATA="${METADATA}" \
  PLAN_ID="${plan_id}" \
  python3 - <<'PY'
import json
import os

print(json.dumps({
    "name": os.environ["CLIENT_NAME"],
    "description": os.environ["CLIENT_DESCRIPTION"],
    "billing_plan_id": os.environ["PLAN_ID"],
    "system_prompt": os.environ["SYSTEM_PROMPT"],
    "metadata_json": os.environ["METADATA"],
    "rate_limit_per_minute": 10,
    "daily_token_quota": 50000,
    "weekly_token_quota": 250000,
    "monthly_token_quota": 1000000,
    "max_context_tokens": 32768,
    "max_output_tokens": 32768,
}))
PY
)"

client_patch_payload="${client_create_payload}"

if [[ -n "${existing_client_id}" ]]; then
  printf '[opencode] cliente já existe (ID: %s), atualizando...\n' "${existing_client_id}"
  client_json="$(
    curl_base_url "${BASE_URL}/admin/clients/${existing_client_id}" -fsS -X PATCH \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "${client_patch_payload}"
  )"
  client_id="${existing_client_id}"
else
  printf '[opencode] criando novo cliente...\n'
  client_json="$(
    curl_base_url "${BASE_URL}/admin/clients" -fsS \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "${client_create_payload}"
  )"
  client_id="$(printf '%s' "${client_json}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')"
fi

printf '[opencode] gerando API key...\n'

key_json="$(
  curl_base_url "${BASE_URL}/admin/api-keys" -fsS \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"client_id\":\"${client_id}\",\"name\":\"opencode-default\"}"
)"

api_key="$(printf '%s' "${key_json}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["api_key"])')"

printf '\n--- CONFIGURAÇÃO SUGERIDA PARA OPENCODE ---\n'
printf 'Endpoint: %s/v1\n' "${BASE_URL}"
printf 'API Key: %s\n' "${api_key}"
printf 'Modelo: gemma (ou qualquer alias ativo)\n'
printf '%s\n' '-------------------------------------------'

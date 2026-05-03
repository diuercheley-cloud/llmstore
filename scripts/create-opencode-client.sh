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

SYSTEM_PROMPT='Você é um assistente de programação prestativo e direto.
Responda diretamente à pergunta do usuário sem preâmbulos desnecessários.
NÃO repita a pergunta do usuário.
NÃO gere blocos de planejamento como "Goal", "Progress", "Done", "In Progress", "Next Steps" ou "Relevant Files", a menos que o usuário peça explicitamente por um relatório de progresso.
Mantenha suas respostas técnicas curtas e focadas na solução.
Se o usuário disser apenas saudações como "oi" ou "olá", responda de forma breve e educada.'

METADATA='{
  "temperature": 0.2,
  "top_p": 0.8,
  "max_tokens": 32768
}'

printf '[opencode] garantindo cliente %s...\n' "${CLIENT_NAME}"

existing_client_id=$(curl -fsS "${BASE_URL}/admin/clients" -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -c "import json, sys; d=json.load(sys.stdin); print([c['id'] for c in d if c['name'] == '${CLIENT_NAME}'][0])" 2>/dev/null || true)

payload="{
  \"name\": \"${CLIENT_NAME}\",
  \"description\": \"${CLIENT_DESCRIPTION}\",
  \"system_prompt\": $(printf '%s' "${SYSTEM_PROMPT}" | python3 -c 'import json, sys; print(json.dumps(sys.stdin.read()))'),
  \"metadata_json\": $(printf '%s' "${METADATA}" | python3 -c 'import json, sys; print(json.dumps(sys.stdin.read()))'),
  \"rate_limit_per_minute\": 10,
  \"daily_token_quota\": 50000,
  \"monthly_token_quota\": 1000000,
  "max_context_tokens": 32768,
  "max_output_tokens": 32768
}"

if [[ -n "${existing_client_id}" ]]; then
  printf '[opencode] cliente já existe (ID: %s), atualizando...\n' "${existing_client_id}"
  client_json="$(
    curl -fsS -X PATCH "${BASE_URL}/admin/clients/${existing_client_id}" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "${payload}"
  )"
  client_id="${existing_client_id}"
else
  printf '[opencode] criando novo cliente...\n'
  client_json="$(
    curl -fsS "${BASE_URL}/admin/clients" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "${payload}"
  )"
  client_id="$(printf '%s' "${client_json}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')"
fi

printf '[opencode] gerando API key...\n'

key_json="$(
  curl -fsS "${BASE_URL}/admin/api-keys" \
    -H "X-Admin-Token: ${ADMIN_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"client_id\":\"${client_id}\",\"name\":\"opencode-default\"}"
)"

api_key="$(printf '%s' "${key_json}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["api_key"])')"

printf '\n--- CONFIGURAÇÃO SUGERIDA PARA OPENCODE ---\n'
printf 'Endpoint: %s/v1\n' "${BASE_URL}"
printf 'API Key: %s\n' "${api_key}"
printf 'Modelo: gemma (ou qualquer alias ativo)\n'
printf '-------------------------------------------\n'

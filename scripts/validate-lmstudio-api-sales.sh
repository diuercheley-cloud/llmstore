#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"

init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-admin-secret-token}"
MODEL="${LMSTUDIO_DEFAULT_MODEL:-nvidia/nemotron-3-nano-4b}"

echo "Verificando /health..."
HEALTH_RESPONSE=$(curl_base_url "${BASE_URL}/health" -fsS)
HEALTH_STATUS=$(echo "$HEALTH_RESPONSE" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("status"))')
if [[ "$HEALTH_STATUS" != "ok" && "$HEALTH_STATUS" != "degraded" ]]; then
    echo "O sistema não está saudável. Status: $HEALTH_STATUS"
    echo "Detalhes: $HEALTH_RESPONSE"
    exit 1
fi
echo "Health OK ($HEALTH_STATUS)"

echo "Consultando plano basic..."
BASIC_PLAN_ID=$(curl_base_url "${BASE_URL}/admin/billing/plans" -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -c '
import json, sys
plans = json.load(sys.stdin)
for p in plans:
    if p.get("code") == "basic":
        print(p.get("id"))
        break
')

if [[ -z "$BASIC_PLAN_ID" ]]; then
    echo "Plano basic não encontrado."
    exit 1
fi

TIMESTAMP=$(date +"%Y%m%d%H%M%S")
CLIENT_NAME="cliente-venda-api-${TIMESTAMP}"

echo "Criando cliente teste ($CLIENT_NAME)..."
CLIENT_PAYLOAD=$(cat <<EOF
{
  "name": "${CLIENT_NAME}",
  "billing_status": "active",
  "billing_plan_id": "${BASIC_PLAN_ID}",
  "rate_limit_per_minute": 10,
  "daily_token_quota": 10000,
  "monthly_token_quota": 50000,
  "max_context_tokens": 4096,
  "max_output_tokens": 1024
}
EOF
)

CLIENT_RESPONSE=$(curl_base_url "${BASE_URL}/admin/clients" -fsS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$CLIENT_PAYLOAD")

CLIENT_ID=$(echo "$CLIENT_RESPONSE" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("id"))')
echo "Cliente criado: $CLIENT_ID"

echo "Criando API Key para cliente..."
KEY_PAYLOAD=$(cat <<EOF
{
  "client_id": "${CLIENT_ID}",
  "name": "key-venda-teste"
}
EOF
)

KEY_RESPONSE=$(curl_base_url "${BASE_URL}/admin/api-keys" -fsS -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$KEY_PAYLOAD")

API_KEY=$(echo "$KEY_RESPONSE" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("api_key"))')
KEY_ID=$(echo "$KEY_RESPONSE" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("id"))')
KEY_PREFIX=$(echo "$KEY_RESPONSE" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("key_prefix"))')
echo "API Key criada com sucesso (Prefixo $KEY_PREFIX)"

echo "Enviando request usando a API Key do cliente..."
CHAT_PAYLOAD=$(cat <<EOF
{
  "model": "${MODEL}",
  "messages": [
    { "role": "user", "content": "Responda em uma frase: o que é BGP?" }
  ],
  "temperature": 0.2,
  "max_tokens": 80,
  "stream": false
}
EOF
)

CHAT_RESPONSE=$(curl_base_url "${BASE_URL}/v1/chat/completions" -fsS -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$CHAT_PAYLOAD")

echo "Resposta da API bruta:"
echo "$CHAT_RESPONSE"

echo "Resposta da API (extraída):"
echo "$CHAT_RESPONSE" | python3 -c 'import json, sys; print(json.load(sys.stdin)["choices"][0]["message"]["content"])'
echo "Tokens usados: $(echo "$CHAT_RESPONSE" | python3 -c 'import json, sys; print(json.load(sys.stdin)["usage"]["total_tokens"])')"

echo "Consultando endpoint admin de uso..."
USAGE_RESPONSE=$(curl_base_url "${BASE_URL}/admin/usage/${CLIENT_ID}/summary" -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}")
echo "Resumo de Uso:"
echo "$USAGE_RESPONSE" | python3 -m json.tool

echo "Revogando a API Key..."
curl_base_url "${BASE_URL}/admin/api-keys/${KEY_ID}" -fsS -X DELETE -H "X-Admin-Token: ${ADMIN_TOKEN}"
echo "Chave revogada."

echo "Testando chave revogada (deve falhar)..."
set +e
ERROR_MSG=$(curl_base_url "${BASE_URL}/v1/chat/completions" -fsS -X POST \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$CHAT_PAYLOAD" 2>&1)
EXIT_CODE=$?
set -e

if [[ $EXIT_CODE -ne 0 ]]; then
    echo "Falhou corretamente. Mensagem/Código de erro capturado no Curl: $EXIT_CODE"
else
    echo "ERRO: A requisição deveria ter falhado!"
    exit 1
fi

echo "----------------------------"
echo "Teste Finalizado com Sucesso"
echo "----------------------------"
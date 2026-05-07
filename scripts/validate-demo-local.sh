#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in .env or environment}"

if [[ ! -f "${ROOT_DIR}/.local/demo-client.env" ]]; then
    echo "ERRO: Arquivo .local/demo-client.env não encontrado. Execute seed-demo-local.sh primeiro."
    exit 1
fi

source "${ROOT_DIR}/.local/demo-client.env"
DEMO_CLIENT_NAME="${DEMO_CLIENT_NAME:-Cliente Demo Local}"

echo "--- Validando Existência do Cliente ---"
client_info=$(curl -fsS "${BASE_URL}/admin/clients" -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -c "import json, sys; 
clients = json.load(sys.stdin)
match = next((c for c in clients if c['name'] == '${DEMO_CLIENT_NAME}'), None)
if match:
    print(f\"ID={match['id']}\")
")
if [[ -n "${client_info}" ]]; then
    echo "OK: Cliente demo encontrado."
else
    echo "FAIL: Cliente demo não encontrado no sistema."
    exit 1
fi

echo "--- Validando API Key ---"
if curl -fsS "${BASE_URL}/v1/models" -H "Authorization: Bearer ${DEMO_API_KEY}" > /dev/null; then
    echo "OK: API Key funciona."
else
    echo "FAIL: API Key não funciona."
    exit 1
fi

echo "--- Validando Chat Completions ---"
chat_resp=$(curl -s -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${DEMO_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [{"role": "user", "content": "Olá, responda apenas OK."}],
    "max_tokens": 5
  }')
if echo "${chat_resp}" | grep -q "choices"; then
    echo "OK: Chat completions funciona."
else
    echo "FAIL: Chat completions falhou."
    echo "${chat_resp}"
    exit 1
fi

echo "--- Validando RAG (se disponível) ---"
rag_status=$(curl -s -H "Authorization: Bearer ${DEMO_API_KEY}" "${BASE_URL}/ready" | grep -q "ready" && echo "ready" || echo "not ready")
if [[ "${rag_status}" == "ready" ]]; then
    query_resp=$(curl -s -X POST "${BASE_URL}/v1/rag/query" \
      -H "Authorization: Bearer ${DEMO_API_KEY}" \
      -H "Content-Type: application/json" \
      -d "{
        \"question\": \"Qual o nome da empresa demo?\",
        \"top_k\": 3
      }")
    if echo "${query_resp}" | grep -qi "TechSolutions"; then
        echo "OK: RAG respondeu corretamente sobre a empresa demo."
    else
        echo "AVISO: RAG respondeu mas não contém 'TechSolutions'. Verifique se a indexação terminou."
        echo "${query_resp}"
    fi
else
    echo "INFO: RAG não está pronto ou habilitado. Pulando teste de query."
fi

echo "--- Validando Invoice ---"
invoices=$(curl -fsS "${BASE_URL}/admin/billing/invoices?client_id=${DEMO_CLIENT_ID}" -H "X-Admin-Token: ${ADMIN_TOKEN}")
if echo "${invoices}" | grep -q "id"; then
    echo "OK: Invoice demo existe."
else
    echo "FAIL: Invoice demo não encontrada."
    exit 1
fi

echo "--- Verificando vazamento de secrets ---"
if git grep -q "${DEMO_API_KEY}" 2>/dev/null; then
    echo "FAIL: API Key demo encontrada no histórico do Git!"
    exit 1
else
    echo "OK: Nenhum secret demo vazado no Git."
fi

echo "VALIDACÃO CONCLUÍDA COM SUCESSO!"

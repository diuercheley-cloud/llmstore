#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in .env or environment}"

CONFIRM="${1:-}"
if [[ "${CONFIRM}" != "--yes" ]]; then
    read -p "Tem certeza que deseja remover todos os dados de DEMO? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

DEMO_CLIENT_NAME="${DEMO_CLIENT_NAME:-Cliente Demo Local}"

echo "--- Buscando cliente demo ---"
client_id=$(curl -fsS "${BASE_URL}/admin/clients" -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -c "import json, sys; 
clients = json.load(sys.stdin)
match = next((c for c in clients if c['name'] == '${DEMO_CLIENT_NAME}'), None)
if match:
    print(match['id'])
")

if [[ -n "${client_id}" ]]; then
    echo "Removendo cliente demo: ${client_id}"
    
    # 1. Deletar RAG files via API (melhor prática para limpar storage também)
    if [[ -f "${ROOT_DIR}/.local/demo-client.env" ]]; then
        source "${ROOT_DIR}/.local/demo-client.env"
        echo "Limpando arquivos RAG..."
        files_json=$(curl -s -H "Authorization: Bearer ${DEMO_API_KEY}" "${BASE_URL}/v1/rag/files")
        if [[ "$(echo "${files_json}" | jq 'type' 2>/dev/null)" == "\"array\"" ]]; then
             for fid in $(echo "${files_json}" | jq -r '.[].id'); do
                 curl -s -X DELETE -H "Authorization: Bearer ${DEMO_API_KEY}" "${BASE_URL}/v1/rag/files/${fid}" > /dev/null
             done
        fi
    fi

    # 2. Deletar dados vinculados ao client_id do demo via DB
    echo "Limpando dados associados ao cliente no banco de dados..."
    # Tabelas que possuem client_id diretamente
    TABLES=("usage_records" "quota_counters" "billing_invoices" "generation_jobs" "security_events" "request_logs" "rag_documents" "api_keys" "rag_document_chunks" "client_feature_blocks" "rag_usage_events")
    
    # customer_payments usa invoice_id, então deletamos primeiro
    dc exec -T postgres psql -U llm_gateway -d llm_gateway -c "DELETE FROM customer_payments WHERE invoice_id IN (SELECT id FROM billing_invoices WHERE client_id = '${client_id}');" > /dev/null
    
    for table in "${TABLES[@]}"; do
        dc exec -T postgres psql -U llm_gateway -d llm_gateway -c "DELETE FROM ${table} WHERE client_id = '${client_id}';" > /dev/null
    done
    
    # 3. Deletar o cliente (hard delete via DB para limpar totalmente)
    dc exec -T postgres psql -U llm_gateway -d llm_gateway -c "DELETE FROM clients WHERE id = '${client_id}';" > /dev/null
    
    echo "Cliente e dados associados removidos com sucesso."
else
    echo "Cliente demo não encontrado."
fi

echo "--- Removendo arquivos temporários ---"
rm -f "${ROOT_DIR}/.local/demo-client.env"

echo "Reset de DEMO concluído."

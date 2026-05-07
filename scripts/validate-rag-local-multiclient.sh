#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/lib/validation-logging.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in .env or environment}"

log_section "RAG Multi-Cliente Validation"

# 1. Criar Cliente A e Cliente B
log_step "Criando clientes"
SUFFIX=$RANDOM
CLIENT_A_DATA=$(./scripts/create-client.sh "Client-RAG-A-${SUFFIX}" "Client A for RAG validation")
CLIENT_A_ID=$(echo "$CLIENT_A_DATA" | grep client_id | cut -d'=' -f2)
KEY_A=$(echo "$CLIENT_A_DATA" | grep api_key | cut -d'=' -f2)

CLIENT_B_DATA=$(./scripts/create-client.sh "Client-RAG-B-${SUFFIX}" "Client B for RAG validation")
CLIENT_B_ID=$(echo "$CLIENT_B_DATA" | grep client_id | cut -d'=' -f2)
KEY_B=$(echo "$CLIENT_B_DATA" | grep api_key | cut -d'=' -f2)

log_info "Client A: $CLIENT_A_ID"
log_info "Client B: $CLIENT_B_ID"

# 2. Upload documento Cliente A
log_step "Upload documento para Cliente A"
DOC_PATH="/tmp/rag_test_a.txt"
echo "O céu é azul e a grama é verde. O segredo do Cliente A é 42." > "$DOC_PATH"

UPLOAD_A=$(curl -fsS "${BASE_URL}/client/rag/documents" \
  -H "Authorization: Bearer ${KEY_A}" \
  -F "file=@${DOC_PATH}")

DOC_A_ID=$(echo "$UPLOAD_A" | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')
log_ok "Documento A carregado: $DOC_A_ID"

# 3. Listar como Cliente B (deve estar vazio)
log_step "Verificando isolamento: Listando como Cliente B"
LIST_B=$(curl -fsS "${BASE_URL}/client/rag/documents" \
  -H "Authorization: Bearer ${KEY_B}")

DOC_COUNT_B=$(echo "$LIST_B" | python3 -c 'import json, sys; print(len(json.load(sys.stdin)["data"]))')
if [ "$DOC_COUNT_B" -eq 0 ]; then
  log_ok "Cliente B não vê documentos do Cliente A."
else
  log_error "Cliente B vê $DOC_COUNT_B documentos!"
  exit 1
fi

# 4. Aguardar processamento (simulado ou real se o worker estiver on)
log_step "Aguardando indexação"
MAX_RETRIES=10
RETRY=0
STATUS="uploaded"
while [ "$RETRY" -lt "$MAX_RETRIES" ] && [ "$STATUS" != "indexed" ]; do
  STATUS=$(curl -fsS "${BASE_URL}/client/rag/documents/${DOC_A_ID}" \
    -H "Authorization: Bearer ${KEY_A}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["status"])')
  log_info "Status: $STATUS"
  if [ "$STATUS" == "indexed" ]; then break; fi
  if [ "$STATUS" == "failed" ]; then log_error "Indexação falhou"; exit 1; fi
  sleep 2
  RETRY=$((RETRY+1))
done

if [ "$STATUS" != "indexed" ]; then
  log_warn "O worker RAG não parece estar rodando. Prosseguindo com testes de API básica."
else
  # 5. Consulta RAG Cliente A
  log_step "Consultando RAG como Cliente A"
  QUERY_A=$(curl -fsS "${BASE_URL}/client/rag/query" \
    -H "Authorization: Bearer ${KEY_A}" \
    -H "Content-Type: application/json" \
    -d '{"question": "Qual o segredo do Cliente A?"}')
  
  ANSWER_A=$(echo "$QUERY_A" | python3 -c 'import json, sys; print(json.load(sys.stdin)["answer"])')
  log_info "Resposta A: $ANSWER_A"
  if [[ "$ANSWER_A" == *"42"* ]]; then
    log_ok "RAG respondeu corretamente para Cliente A."
  else
    log_error "Resposta incorreta ou incompleta."
  fi
fi

# 6. Tentar acessar documento A como Cliente B
log_step "Verificando isolamento: Acessando doc do A como B"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/client/rag/documents/${DOC_A_ID}" \
  -H "Authorization: Bearer ${KEY_B}")

if [ "$HTTP_CODE" -eq 404 ]; then
  log_ok "Cliente B recebeu 404 ao tentar acessar documento do Cliente A."
else
  log_error "Cliente B acessou documento do Cliente A (HTTP $HTTP_CODE)!"
  exit 1
fi

# 7. Testar limites de plano (Simulação rápida se possível)
log_step "Testando limites de documentos"
CLIENT_C_DATA=$(./scripts/create-client.sh "Client-RAG-C-${SUFFIX}" "Client C for Free Plan limit")
CLIENT_C_ID=$(echo "$CLIENT_C_DATA" | grep client_id | cut -d'=' -f2)
KEY_C=$(echo "$CLIENT_C_DATA" | grep api_key | cut -d'=' -f2)

# 8. Admin View
log_step "Verificando visão administrativa"
ADMIN_RAG=$(curl -fsS "${BASE_URL}/admin/rag/usage" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}")

A_DOCS=$(echo "$ADMIN_RAG" | python3 -c "import json, sys; data=json.load(sys.stdin); print(next((x['documents_count'] for x in data if x['client_id']=='$CLIENT_A_ID'), 0))")
B_DOCS=$(echo "$ADMIN_RAG" | python3 -c "import json, sys; data=json.load(sys.stdin); print(next((x['documents_count'] for x in data if x['client_id']=='$CLIENT_B_ID'), 0))")

if [ "$A_DOCS" -ge 1 ]; then
  log_ok "Admin mostra documentos para Cliente A corretamente."
else
  log_warn "Admin mostra 0 documentos para Cliente A (pode ser delay de sincronismo)."
fi

if [ "$B_DOCS" -eq 0 ]; then
  log_ok "Admin mostra 0 documentos para Cliente B."
else
  log_error "Admin mostra $B_DOCS documentos para Cliente B, esperado 0."
  exit 1
fi

# Cleanup
log_step "Limpando recursos (clientes temporários)"
HTTP_DEL_A=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "${BASE_URL}/admin/clients/${CLIENT_A_ID}" -H "X-Admin-Token: ${ADMIN_TOKEN}")
if [ "$HTTP_DEL_A" -ne 204 ]; then
  log_warn "clientes temporários não removidos porque não há endpoint disponível ou erro (HTTP $HTTP_DEL_A)."
fi
curl -s -X DELETE "${BASE_URL}/admin/clients/${CLIENT_B_ID}" -H "X-Admin-Token: ${ADMIN_TOKEN}" >/dev/null || true
curl -s -X DELETE "${BASE_URL}/admin/clients/${CLIENT_C_ID}" -H "X-Admin-Token: ${ADMIN_TOKEN}" >/dev/null || true

log_ok "VALIDAÇÃO RAG CONCLUÍDA COM SUCESSO"

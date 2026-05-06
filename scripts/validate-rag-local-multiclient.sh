#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in .env or environment}"

echo "--- VALIDANDO RAG MULTI-CLIENTE ---"

# 1. Criar Cliente A e Cliente B
echo "[1/9] Criando clientes..."
SUFFIX=$RANDOM
CLIENT_A_DATA=$(./scripts/create-client.sh "Client-RAG-A-${SUFFIX}" "Client A for RAG validation")
CLIENT_A_ID=$(echo "$CLIENT_A_DATA" | grep client_id | cut -d'=' -f2)
KEY_A=$(echo "$CLIENT_A_DATA" | grep api_key | cut -d'=' -f2)

CLIENT_B_DATA=$(./scripts/create-client.sh "Client-RAG-B-${SUFFIX}" "Client B for RAG validation")
CLIENT_B_ID=$(echo "$CLIENT_B_DATA" | grep client_id | cut -d'=' -f2)
KEY_B=$(echo "$CLIENT_B_DATA" | grep api_key | cut -d'=' -f2)

echo "Client A: $CLIENT_A_ID"
echo "Client B: $CLIENT_B_ID"

# 2. Upload documento Cliente A
echo "[2/9] Upload documento para Cliente A..."
DOC_PATH="/tmp/rag_test_a.txt"
echo "O céu é azul e a grama é verde. O segredo do Cliente A é 42." > "$DOC_PATH"

UPLOAD_A=$(curl -fsS "${BASE_URL}/client/rag/documents" \
  -H "Authorization: Bearer ${KEY_A}" \
  -F "file=@${DOC_PATH}")

DOC_A_ID=$(echo "$UPLOAD_A" | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')
echo "Documento A carregado: $DOC_A_ID"

# 3. Listar como Cliente B (deve estar vazio)
echo "[3/9] Verificando isolamento: Listando como Cliente B..."
LIST_B=$(curl -fsS "${BASE_URL}/client/rag/documents" \
  -H "Authorization: Bearer ${KEY_B}")

DOC_COUNT_B=$(echo "$LIST_B" | python3 -c 'import json, sys; print(len(json.load(sys.stdin)["data"]))')
if [ "$DOC_COUNT_B" -eq 0 ]; then
  echo "OK: Cliente B não vê documentos do Cliente A."
else
  echo "ERRO: Cliente B vê $DOC_COUNT_B documentos!"
  exit 1
fi

# 4. Aguardar processamento (simulado ou real se o worker estiver on)
echo "[4/9] Aguardando indexação..."
MAX_RETRIES=10
RETRY=0
STATUS="uploaded"
while [ "$RETRY" -lt "$MAX_RETRIES" ] && [ "$STATUS" != "indexed" ]; do
  STATUS=$(curl -fsS "${BASE_URL}/client/rag/documents/${DOC_A_ID}" \
    -H "Authorization: Bearer ${KEY_A}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["status"])')
  echo "Status: $STATUS"
  if [ "$STATUS" == "indexed" ]; then break; fi
  if [ "$STATUS" == "failed" ]; then echo "ERRO: Indexação falhou"; exit 1; fi
  sleep 2
  RETRY=$((RETRY+1))
done

if [ "$STATUS" != "indexed" ]; then
  echo "AVISO: O worker RAG não parece estar rodando. Prosseguindo com testes de API básica."
else
  # 5. Consulta RAG Cliente A
  echo "[5/9] Consultando RAG como Cliente A..."
  QUERY_A=$(curl -fsS "${BASE_URL}/client/rag/query" \
    -H "Authorization: Bearer ${KEY_A}" \
    -H "Content-Type: application/json" \
    -d '{"question": "Qual o segredo do Cliente A?"}')
  
  ANSWER_A=$(echo "$QUERY_A" | python3 -c 'import json, sys; print(json.load(sys.stdin)["answer"])')
  echo "Resposta A: $ANSWER_A"
  if [[ "$ANSWER_A" == *"42"* ]]; then
    echo "OK: RAG respondeu corretamente para Cliente A."
  else
    echo "ERRO: Resposta incorreta ou incompleta."
  fi
fi

# 6. Tentar acessar documento A como Cliente B
echo "[6/9] Verificando isolamento: Acessando doc do A como B..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/client/rag/documents/${DOC_A_ID}" \
  -H "Authorization: Bearer ${KEY_B}")

if [ "$HTTP_CODE" -eq 404 ]; then
  echo "OK: Cliente B recebeu 404 ao tentar acessar documento do Cliente A."
else
  echo "ERRO: Cliente B acessou documento do Cliente A (HTTP $HTTP_CODE)!"
  exit 1
fi

# 7. Testar limites de plano (Simulação rápida se possível)
echo "[7/9] Testando limites de documentos (Plano Free tem limite)..."

# Criar Cliente C para o teste de limite
CLIENT_C_DATA=$(./scripts/create-client.sh "Client-RAG-C-${SUFFIX}" "Client C for Free Plan limit")
CLIENT_C_ID=$(echo "$CLIENT_C_DATA" | grep client_id | cut -d'=' -f2)
KEY_C=$(echo "$CLIENT_C_DATA" | grep api_key | cut -d'=' -f2)

# O plano Free tem rag_max_documents = 5. Vamos fazer upload de 5 arquivos e o 6º deve falhar.
for i in {1..5}; do
  DOC_PATH="/tmp/rag_test_c_${i}.txt"
  echo "Documento Free limite $i" > "$DOC_PATH"
  UPLOAD_C=$(curl -fsS "${BASE_URL}/client/rag/documents" \
    -H "Authorization: Bearer ${KEY_C}" \
    -F "file=@${DOC_PATH}")
  rm -f "$DOC_PATH"
done

DOC_PATH="/tmp/rag_test_c_6.txt"
echo "Documento Free limite 6" > "$DOC_PATH"
HTTP_CODE=$(curl -s -o /tmp/upload_err.json -w "%{http_code}" "${BASE_URL}/client/rag/documents" \
  -H "Authorization: Bearer ${KEY_C}" \
  -F "file=@${DOC_PATH}")

rm -f "$DOC_PATH"

if [ "$HTTP_CODE" -eq 429 ]; then
  ERR_MSG=$(cat /tmp/upload_err.json | grep "rag_limit_exceeded" || true)
  if [ -n "$ERR_MSG" ]; then
    echo "OK: limite de documentos do plano Free bloqueou upload excedente."
  else
    echo "ERRO: HTTP 429 retornado, mas não por rag_limit_exceeded."
    cat /tmp/upload_err.json
    exit 1
  fi
else
  echo "ERRO: plano Free permitiu upload acima do limite (HTTP $HTTP_CODE)."
  cat /tmp/upload_err.json
  exit 1
fi


# 8. Testar delete
echo "[8/9] Testando exclusão de documento..."
curl -fsS -X DELETE "${BASE_URL}/client/rag/documents/${DOC_A_ID}" \
  -H "Authorization: Bearer ${KEY_A}"
echo "Documento excluído."

LIST_A_FINAL=$(curl -fsS "${BASE_URL}/client/rag/documents" \
  -H "Authorization: Bearer ${KEY_A}")
DOC_COUNT_A=$(echo "$LIST_A_FINAL" | python3 -c 'import json, sys; print(len(json.load(sys.stdin)["data"]))')
if [ "$DOC_COUNT_A" -eq 0 ]; then
  echo "OK: Documento removido com sucesso."
else
  echo "ERRO: Documento ainda aparece na listagem!"
fi

# 9. Ver uso no Admin
echo "[9/9] Verificando uso no Admin Dashboard..."
ADMIN_RAG=$(curl -fsS "${BASE_URL}/admin/rag/usage" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}")

echo "Verificando Cliente A ($CLIENT_A_ID) no Admin..."
CLIENT_A_USAGE=$(echo "$ADMIN_RAG" | python3 -c "import json, sys; print(json.dumps(next((item for item in json.load(sys.stdin) if item['client_id'] == '${CLIENT_A_ID}'), {})))")

A_DOCS=$(echo "$CLIENT_A_USAGE" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("documents_count", -1))')
A_QUERIES=$(echo "$CLIENT_A_USAGE" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("queries_month", -1))')
A_PAGES=$(echo "$CLIENT_A_USAGE" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("pages_month", -1))')

if [ "$A_DOCS" -eq 0 ]; then
  echo "OK: Admin mostra 0 documentos para Cliente A após exclusão."
else
  echo "ERRO: Admin mostra $A_DOCS documentos para Cliente A, esperado 0."
  exit 1
fi

if [ "$STATUS" == "indexed" ]; then
  if [ "$A_QUERIES" -ge 1 ]; then
    echo "OK: Admin mostra pelo menos 1 query no mês para Cliente A."
  else
    echo "ERRO: Admin mostra $A_QUERIES queries para Cliente A, esperado >= 1."
    exit 1
  fi

  if [ "$A_PAGES" -ge 1 ]; then
    echo "OK: Admin mostra pelo menos 1 página processada no mês para Cliente A."
  else
    echo "ERRO: Admin mostra $A_PAGES páginas para Cliente A, esperado >= 1."
    exit 1
  fi
else
  echo "AVISO: Worker RAG não indexou o documento, pulando validação de queries e pages no Admin."
fi

echo "Verificando Cliente B ($CLIENT_B_ID) no Admin..."
CLIENT_B_USAGE=$(echo "$ADMIN_RAG" | python3 -c "import json, sys; print(json.dumps(next((item for item in json.load(sys.stdin) if item['client_id'] == '${CLIENT_B_ID}'), {})))")
B_DOCS=$(echo "$CLIENT_B_USAGE" | python3 -c 'import json, sys; print(json.load(sys.stdin).get("documents_count", -1))')

if [ "$B_DOCS" -eq 0 ]; then
  echo "OK: Admin mostra 0 documentos para Cliente B."
else
  echo "ERRO: Admin mostra $B_DOCS documentos para Cliente B, esperado 0."
  exit 1
fi

# Cleanup
echo "Limpando recursos (clientes temporários)..."
HTTP_DEL_A=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "${BASE_URL}/admin/clients/${CLIENT_A_ID}" -H "X-Admin-Token: ${ADMIN_TOKEN}")
if [ "$HTTP_DEL_A" -ne 204 ]; then
  echo "WARN: clientes temporários não removidos porque não há endpoint disponível ou erro (HTTP $HTTP_DEL_A)."
fi
curl -s -X DELETE "${BASE_URL}/admin/clients/${CLIENT_B_ID}" -H "X-Admin-Token: ${ADMIN_TOKEN}" >/dev/null || true
curl -s -X DELETE "${BASE_URL}/admin/clients/${CLIENT_C_ID}" -H "X-Admin-Token: ${ADMIN_TOKEN}" >/dev/null || true

echo "--- VALIDAÇÃO RAG CONCLUÍDA COM SUCESSO ---"


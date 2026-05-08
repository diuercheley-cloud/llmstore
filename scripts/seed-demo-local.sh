#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

if [[ -z "${ADMIN_TOKEN:-}" ]]; then
    echo "ERRO: ADMIN_TOKEN não definido. Verifique seu arquivo .env"
    exit 1
fi

BASE_URL="${BASE_URL:-$(default_base_url)}"

# Default demo values
DEMO_MODE="${DEMO_MODE:-false}"
if [[ "${DEMO_MODE}" != "true" ]]; then
    echo "AVISO: DEMO_MODE não está como true no ambiente."
fi

DEMO_CLIENT_NAME="${DEMO_CLIENT_NAME:-Cliente Demo Local}"
DEMO_CLIENT_EMAIL="${DEMO_CLIENT_EMAIL:-demo@example.local}"
DEMO_PLAN="${DEMO_PLAN:-demo-pro}"

echo "--- Verificando se a stack está ativa ---"
if ! curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
    echo "ERRO: Stack não encontrada em ${BASE_URL}. Inicie com ./scripts/up.sh primeiro."
    exit 1
fi

echo "--- Criando plano demo: ${DEMO_PLAN} ---"
plan_exists=$(curl -fsS "${BASE_URL}/admin/billing/plans" -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -c "import json, sys; print(any(p['code'] == '${DEMO_PLAN}' for p in json.load(sys.stdin)))")

if [[ "${plan_exists}" == "False" ]]; then
    "${SCRIPT_DIR}/create-plan.sh" "${DEMO_PLAN}" "Plano Demo Pro" 20 100000 500000 1000000 1024 true "Plano para demonstração local"
else
    echo "Plano ${DEMO_PLAN} já existe."
fi

echo "--- Criando cliente demo: ${DEMO_CLIENT_NAME} ---"
client_info=$(curl -fsS "${BASE_URL}/admin/clients" -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -c "import json, sys; 
clients = json.load(sys.stdin)
match = next((c for c in clients if c['name'] == '${DEMO_CLIENT_NAME}'), None)
if match:
    print(f\"ID={match['id']}\")
")

if [[ -z "${client_info}" ]]; then
    client_output="$("${SCRIPT_DIR}/create-client.sh" "${DEMO_CLIENT_NAME}" "Cliente para demonstração local")"
    CLIENT_ID="$(printf '%s\n' "${client_output}" | awk -F= '/^client_id=/{print $2}' | tail -n1)"
    API_KEY="$(printf '%s\n' "${client_output}" | awk -F= '/^api_key=/{print $2}' | tail -n1)"
    echo "Cliente demo criado com ID: ${CLIENT_ID}"
else
    CLIENT_ID=$(echo "${client_info}" | cut -d= -f2)
    echo "Cliente demo já existe com ID: ${CLIENT_ID}"
    # Issue a fresh key for the demo session
    key_json="$(
      curl -fsS "${BASE_URL}/admin/api-keys" \
        -H "X-Admin-Token: ${ADMIN_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"client_id\":\"${CLIENT_ID}\",\"name\":\"demo-key-$(date +%s)\"}"
    )"
    API_KEY=$(printf '%s' "${key_json}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["api_key"])')
fi

# Save to .local/demo-client.env
mkdir -p "${ROOT_DIR}/.local"
cat <<EOF > "${ROOT_DIR}/.local/demo-client.env"
# DEMO CLIENT CONFIGURATION - DO NOT COMMIT
DEMO_CLIENT_ID=${CLIENT_ID}
DEMO_API_KEY=${API_KEY}
DEMO_BASE_URL=${BASE_URL}
EOF
chmod 600 "${ROOT_DIR}/.local/demo-client.env"
echo "Chave API salva em .local/demo-client.env"

echo "--- Vinculando cliente ao plano demo ---"
"${SCRIPT_DIR}/set-client-plan.sh" "${CLIENT_ID}" "${DEMO_PLAN}" >/dev/null

echo "--- Gerando uso sintético ---"
for i in {1..3}; do
    curl -s -X POST "${BASE_URL}/v1/chat/completions" \
      -H "Authorization: Bearer ${API_KEY}" \
      -H "Content-Type: application/json" \
      -d '{
        "model": "default",
        "messages": [{"role": "user", "content": "Olá, sou o cliente demo."}],
        "max_tokens": 10
      }' > /dev/null
done

echo "--- Gerando invoice demo ---"
"${SCRIPT_DIR}/generate-invoices.sh" "${CLIENT_ID}" 7 "Fatura de demonstração local" > /dev/null

echo "--- Indexando documentos RAG demo ---"
if [[ -d "${ROOT_DIR}/demo/rag-documents" ]]; then
    for f in "${ROOT_DIR}/demo/rag-documents"/*; do
        if [[ -f "$f" ]]; then
            echo "Fazendo upload de: $(basename "$f")"
            curl -s -X POST "${BASE_URL}/client/rag/documents" \
              -H "Authorization: Bearer ${API_KEY}" \
              -F "file=@${f}" > /dev/null
        fi
    done
fi

echo "--- Validando acesso básico ---"
if curl -fsS "${BASE_URL}/v1/models" -H "Authorization: Bearer ${API_KEY}" > /dev/null; then
    echo "VALIDAÇÃO: Cliente demo consegue listar modelos."
else
    echo "ERRO: Falha na validação do cliente demo."
    exit 1
fi

echo "################################################"
echo "Demo SEED concluído com sucesso!"
echo "ID Cliente: ${CLIENT_ID}"
echo "API Key: ${API_KEY}"
echo "Configuração salva em: .local/demo-client.env"
echo "################################################"

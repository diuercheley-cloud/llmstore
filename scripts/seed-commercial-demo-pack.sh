#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"

if [[ -z "${ADMIN_TOKEN:-}" ]]; then
    echo "ERRO: ADMIN_TOKEN não definido. Verifique seu arquivo .env"
    exit 1
fi

RESET_FIRST=false
DRY_RUN=false
for arg in "$@"; do
    case "$arg" in
        --reset) RESET_FIRST=false ;;
        --dry-run) DRY_RUN=false ;;
    esac
done

if [[ "$RESET_FIRST" == true ]]; then
    echo "--- Resetando demo pack anterior ---"
    "${SCRIPT_DIR}/reset-commercial-demo-pack.sh" --yes 2>/dev/null || echo "  Script reset não encontrado, continuando..."
fi

if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY-RUN] Simulando criação do demo pack..."
fi

echo "--- Verificando se a stack está ativa ---"
if ! curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
    echo "ERRO: Stack não encontrada em ${BASE_URL}. Inicie com ./scripts/up.sh primeiro."
    exit 1
fi

create_or_update_plan() {
    local payload=$1
    local code
    code=$(echo "$payload" | python3 -c "import sys, json; print(json.load(sys.stdin)['code'])")
    echo "  Processando plano: ${code}..."
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/admin/billing/plans" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$payload")
    if [[ "$response" == "201" ]] || [[ "$response" == "200" ]]; then
        echo "    Plano ${code} criado."
    elif [[ "$response" == "409" ]]; then
        echo "    Plano ${code} já existe, atualizando..."
        local plan_id
        plan_id=$(curl -s "${BASE_URL}/admin/billing/plans" \
          -H "X-Admin-Token: ${ADMIN_TOKEN}" | \
          python3 -c "import sys, json; print([p['id'] for p in json.load(sys.stdin) if p['code'] == '${code}'][0])")
        curl -s -X PATCH "${BASE_URL}/admin/billing/plans/${plan_id}" \
          -H "X-Admin-Token: ${ADMIN_TOKEN}" \
          -H "Content-Type: application/json" \
          -d "$payload" > /dev/null
        echo "    Plano ${code} atualizado."
    else
        echo "    Erro plano ${code}: HTTP ${response}"
        return 1
    fi
}

echo ""
echo "=============================================="
echo "  DEMO PACK COMERCIAL - SEED"
echo "=============================================="
echo ""

echo "--- Criando planos demo (do fake-data) ---"

# shellcheck source=/dev/null
FAKE_DIR="${ROOT_DIR}/demo-pack/fake-data"
FAKE_PLANS="${FAKE_DIR}/plans.json"
FAKE_CLIENTS="${FAKE_DIR}/clients.json"

if [[ ! -f "$FAKE_PLANS" ]] || [[ ! -f "$FAKE_CLIENTS" ]]; then
    echo "ERRO: Arquivos fake-data nao encontrados em ${FAKE_DIR}/"
    exit 1
fi

if [[ "$DRY_RUN" == false ]]; then
    while IFS=$'\n' read -r plan_json; do
        [[ -z "$plan_json" ]] && continue
        create_or_update_plan "$plan_json"
    done < <(python3 -c "
import json, sys
with open('$FAKE_PLANS') as f:
    data = json.load(f)
for p in data['plans']:
    # Map to API expected format (keep only relevant fields)
    payload = {
        'code': p['code'],
        'name': p['name'],
        'description': p['description'],
        'rate_limit_per_minute': p['rate_limit_per_minute'],
        'daily_token_quota': p['daily_token_quota'],
        'weekly_token_quota': p.get('weekly_token_quota', p['daily_token_quota'] * 5),
        'monthly_token_quota': p['monthly_token_quota'],
        'requests_per_day': p['requests_per_day'],
        'requests_per_month': p['requests_per_month'],
        'max_context_tokens': p['max_context_tokens'],
        'max_output_tokens': p['max_output_tokens'],
        'allow_streaming': p['allow_streaming'],
        'rag_enabled': p['rag_enabled'],
        'rag_max_documents': p['rag_max_documents'],
        'rag_max_storage_mb': p['rag_max_storage_mb'],
        'rag_max_pages_per_month': p.get('rag_max_pages_per_month', 50),
        'rag_max_queries_per_month': p.get('rag_max_queries_per_month', 500),
        'tts_enabled': p['tts_enabled'],
        'tts_chars_per_request': p.get('tts_chars_per_request', 500),
        'tts_chars_per_day': p.get('tts_chars_per_day', 3000),
        'tts_chars_per_month': p['tts_chars_per_month'],
        'embeddings_enabled': p['embeddings_enabled'],
        'embeddings_requests_per_month': p['embeddings_requests_per_month'],
        'embeddings_tokens_per_month': p['embeddings_tokens_per_month'],
        'responses_enabled': p['responses_enabled'],
        'tools_enabled': p['tools_enabled'],
        'export_enabled': p['export_enabled'],
        'support_level': p['support_level'],
        'price_brl': p['monthly_price_brl'],
        'is_active': p.get('is_active', True),
        'allowed_models': p['allowed_models']
    }
    print(json.dumps(payload))
")
fi

echo ""
echo "--- Criando clientes demo (do fake-data) ---"

# Read client data from fake-data
declare -A CLIENT_NAMES
declare -A CLIENT_DESCS
declare -A CLIENT_PLANS
CLIENT_SCENARIOS=()

while IFS='|' read -r scenario name desc plan_code; do
    [[ -z "$scenario" ]] && continue
    CLIENT_SCENARIOS+=("$scenario")
    CLIENT_NAMES["$scenario"]="$name"
    CLIENT_DESCS["$scenario"]="$desc"
    CLIENT_PLANS["$scenario"]="$plan_code"
done < <(python3 -c "
import json, sys
with open('$FAKE_CLIENTS') as f:
    data = json.load(f)
for c in data['clients']:
    print(f\"{c['scenario']}|{c['name']}|{c['description']}|{c['plan_code']}\")
")
CLIENT_IDS=()
API_KEY_FILE="${ROOT_DIR}/.local/demo-commercial-clients.env"

if [[ "$DRY_RUN" == false ]]; then
    mkdir -p "${ROOT_DIR}/.local"
    cat <<EOF > "$API_KEY_FILE"
# DEMO COMMERCIAL CLIENTS - DO NOT COMMIT
# Generated by seed-commercial-demo-pack.sh on $(date)
# ALL DATA IS FICTIONAL - DEMO PURPOSES ONLY
EOF
    chmod 600 "$API_KEY_FILE"
fi

for scenario in "${CLIENT_SCENARIOS[@]}"; do
    client_name="${CLIENT_NAMES[$scenario]}"
    client_desc="${CLIENT_DESCS[$scenario]}"
    client_plan="${CLIENT_PLANS[$scenario]}"

    echo ""
    echo "  Cenário: ${scenario} -> ${client_name}"

    if [[ "$DRY_RUN" == true ]]; then
        echo "    [DRY-RUN] Criaria cliente, plano ${client_plan}, API key, RAG, invoice"
        CLIENT_IDS+=("dry-run-${scenario}")
        continue
    fi

    existing_id=$(curl -fsS "${BASE_URL}/admin/clients" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" | \
      python3 -c "import json, sys; clients = json.load(sys.stdin); match = next((c for c in clients if c['name'] == '${client_name}'), None); print(json.dumps(match['id']) if match else '')")

    if [[ -n "$existing_id" && "$existing_id" != '""' ]]; then
        CLIENT_ID=$(echo "$existing_id" | tr -d '"')
        echo "    Cliente já existe com ID: ${CLIENT_ID}"
    else
        create_payload=$(python3 -c '
import json
name = "'"${client_name}"'"
desc = "'"${client_desc}"'"
metadata = json.dumps({"demo": True, "scenario": "'"${scenario}"'", "ficticio": True, "demo_pack": "v1.0"})
payload = {
    "name": name,
    "description": desc,
    "metadata_json": metadata,
    "rate_limit_per_minute": 30,
    "daily_token_quota": 150000,
    "monthly_token_quota": 3000000,
    "max_context_tokens": 8192,
    "max_output_tokens": 2048
}
print(json.dumps(payload))
')
        client_output=$(curl -fsS "${BASE_URL}/admin/clients" \
          -H "X-Admin-Token: ${ADMIN_TOKEN}" \
          -H "Content-Type: application/json" \
          -d "$create_payload")
        CLIENT_ID=$(printf '%s' "${client_output}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')
        echo "    Criado com ID: ${CLIENT_ID}"
    fi

    key_json=$(curl -fsS "${BASE_URL}/admin/api-keys" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"client_id\": \"${CLIENT_ID}\", \"name\": \"demo-${scenario}-key\"}")
    API_KEY=$(printf '%s' "${key_json}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["api_key"])')
    echo "    API Key gerada: sk-demo-****${API_KEY: -8}"

    CLIENT_IDS+=("$CLIENT_ID")

    echo "    Salvando credenciais..."
    cat <<EOF >> "$API_KEY_FILE"
DEMO_CLIENT_${scenario^^}_ID=${CLIENT_ID}
DEMO_CLIENT_${scenario^^}_NAME=${client_name}
DEMO_CLIENT_${scenario^^}_API_KEY=${API_KEY}
EOF

    echo "    Vinculando ao plano ${client_plan}..."
    plan_id=$(curl -fsS "${BASE_URL}/admin/billing/plans" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" | \
      python3 -c "import json, sys; plans = json.load(sys.stdin); match = next((p for p in plans if p['code'] == '${client_plan}'), None); print(json.dumps(match['id']) if match else '')")

    if [[ -n "$plan_id" && "$plan_id" != '""' ]]; then
        plan_id_clean=$(echo "$plan_id" | tr -d '"')
        curl -s -X PATCH "${BASE_URL}/admin/clients/${CLIENT_ID}/billing-plan" \
          -H "X-Admin-Token: ${ADMIN_TOKEN}" \
          -H "Content-Type: application/json" \
          -d "{\"billing_plan_id\": \"${plan_id_clean}\"}" > /dev/null
        echo "    Plano vinculado."
    else
        echo "    AVISO: Plano ${client_plan} não encontrado."
    fi

    echo "    Gerando uso sintético (3 chamadas)..."
    for j in {1..3}; do
        curl -s -X POST "${BASE_URL}/v1/chat/completions" \
          -H "Authorization: Bearer ${API_KEY}" \
          -H "Content-Type: application/json" \
          -d '{"model":"default","messages":[{"role":"user","content":"Olá, sou um cliente demo comercial."}],"max_tokens":10}' > /dev/null 2>&1 || true
    done

    # Load RAG documents from fake-data (source of truth)
    case "$scenario" in
        clinica) doc_file="${FAKE_DIR}/rag_documents/politica_interna_horizonte.txt" ;;
        juridico) doc_file="${FAKE_DIR}/rag_documents/contrato_atlas.txt" ;;
        suporte) doc_file="${FAKE_DIR}/rag_documents/manual_suporte_orion.txt" ;;
        educacao) doc_file="${FAKE_DIR}/rag_documents/faq_prisma.txt" ;;
        provedor-api) doc_file="${FAKE_DIR}/rag_documents/base_conhecimento_nebula.txt" ;;
    esac

    if [[ -f "$doc_file" ]]; then
        echo "    Upload RAG: $(basename "$doc_file")..."
        curl -s -X POST "${BASE_URL}/client/rag/documents" \
          -H "Authorization: Bearer ${API_KEY}" \
          -F "file=@${doc_file}" > /dev/null 2>&1 || echo "    AVISO: RAG upload falhou (backend pode estar offline)"
    fi

    echo "    Gerando invoice demo..."
    "${SCRIPT_DIR}/generate-invoices.sh" "${CLIENT_ID}" 7 "Fatura demonstrativa - demo pack comercial" > /dev/null 2>&1 || echo "    AVISO: Geração de invoice falhou (pode já existir)"
done

echo ""
echo "--- Verificando dados no Admin Dashboard ---"
if [[ "$DRY_RUN" == false ]]; then
    demo_summary=$(curl -fsS "${BASE_URL}/admin/demo/summary" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null || echo '{"error":"unavailable"}')
    echo "  Demo summary: $(echo "$demo_summary" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("enabled" if d.get("demo_enabled") else "check dashboard")')"
fi

echo ""
echo "=============================================="
echo "  DEMO PACK COMERCIAL - SEED CONCLUÍDO"
echo "=============================================="
echo ""
echo "Clientes demo criados (dados 100% fictícios):"
for scenario in "${CLIENT_SCENARIOS[@]}"; do
    echo "  [${scenario}] ${CLIENT_NAMES[$scenario]}"
done
echo ""
echo "Credenciais salvas em: .local/demo-commercial-clients.env"
echo "Admin Dashboard: ${BASE_URL}/admin-dashboard"
echo "Client Portal:   ${BASE_URL}/client-portal"
echo "Admin Lab:       ${BASE_URL}/admin-lab"
echo ""
echo "Para validar: make validate-demo-pack"
echo "Para testar:   source .local/demo-commercial-clients.env"
echo "=============================================="

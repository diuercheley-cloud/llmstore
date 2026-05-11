#!/usr/bin/env bash
set -euo pipefail

# scripts/validate-rate-limit-readiness-local.sh
# Prova segura de rate limit para Production Readiness.
# Cria plano/cliente temporários com limite baixo e verifica 429.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
# shellcheck source=/dev/null
if [[ -f "${SCRIPT_DIR}/lib/validation-logging.sh" ]]; then
  source "${SCRIPT_DIR}/lib/validation-logging.sh"
fi
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment}"
PLAN_CODE="readiness-rate-limit-test"
CLIENT_NAME="readiness-rate-limit-probe-$(date +%s)"
TEMP_DIR=$(mktemp -d)

log_info "Iniciando prova segura de rate limit em ${BASE_URL}..."

# 1. Garantir que o plano existe
log_info "Criando/Verificando plano temporário: ${PLAN_CODE} (2 RPM)"
PLAN_RESPONSE=$(curl -s -X POST "${BASE_URL}/admin/billing/plans" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"code\": \"${PLAN_CODE}\",
    \"name\": \"Readiness Rate Limit Test\",
    \"description\": \"Plano temporário para validação de rate limit\",
    \"rate_limit_per_minute\": 2,
    \"daily_token_quota\": 1000,
    \"weekly_token_quota\": 5000,
    \"monthly_token_quota\": 10000,
    \"max_output_tokens\": 64,
    \"allow_streaming\": true,
    \"tts_enabled\": true,
    \"rag_enabled\": true
  }")

# Se 409, o plano já existe, buscamos o ID.
PLAN_ID=$(echo "${PLAN_RESPONSE}" | jq -r '.id // empty')
if [[ -z "${PLAN_ID}" ]]; then
    PLAN_ID=$(curl -s -H "X-Admin-Token: ${ADMIN_TOKEN}" "${BASE_URL}/admin/billing/plans" | jq -r ".[] | select(.code == \"${PLAN_CODE}\") | .id")
fi

if [[ -z "${PLAN_ID}" || "${PLAN_ID}" == "null" ]]; then
    log_error "Falha ao obter PLAN_ID para ${PLAN_CODE}"
    exit 1
fi
log_info "PLAN_ID: ${PLAN_ID}"

# 2. Criar cliente temporário associado ao plano
log_info "Criando cliente temporário: ${CLIENT_NAME}"
CLIENT_RESPONSE=$(curl -s -X POST "${BASE_URL}/admin/clients" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"${CLIENT_NAME}\",
    \"description\": \"Cliente temporário para probe de rate limit\",
    \"billing_plan_id\": \"${PLAN_ID}\"
  }")

CLIENT_ID=$(echo "${CLIENT_RESPONSE}" | jq -r '.id // empty')
if [[ -z "${CLIENT_ID}" || "${CLIENT_ID}" == "null" ]]; then
    log_error "Falha ao criar cliente"
    echo "${CLIENT_RESPONSE}"
    exit 1
fi

# 3. Criar API key
log_info "Criando API key para cliente ${CLIENT_ID}"
KEY_RESPONSE=$(curl -s -X POST "${BASE_URL}/admin/api-keys" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"client_id\":\"${CLIENT_ID}\",\"name\":\"readiness-probe\"}")

API_KEY=$(echo "${KEY_RESPONSE}" | jq -r '.api_key // empty')
if [[ -z "${API_KEY}" || "${API_KEY}" == "null" ]]; then
    log_error "Falha ao criar API key"
    exit 1
fi

# Cleanup function
cleanup() {
    log_info "Limpando recursos temporários..."
    if [[ -n "${CLIENT_ID:-}" ]]; then
        curl -s -X DELETE "${BASE_URL}/admin/clients/${CLIENT_ID}" -H "X-Admin-Token: ${ADMIN_TOKEN}" > /dev/null || true
    fi
    # Plano pode ser mantido ou removido. Se criamos agora, removemos.
    # Mas admin.py não parece ter DELETE /admin/billing/plans/{id} exposto no trecho que li.
    # Vou checar se existe DELETE para planos.
    rm -rf "${TEMP_DIR}"
}
trap cleanup EXIT

# 4. Executar probe (requisições leves até estourar 2 RPM)
log_info "Executando requisições de teste em /portal/test-chat (Limite: 2 RPM)..."

# Identificar um modelo para o teste
MODEL_ID=$(curl -s -H "Authorization: Bearer ${API_KEY}" "${BASE_URL}/v1/models" | jq -r '.data[0].id // "default"')

STATUSES=()
for i in {1..4}; do
    # Usando /portal/test-chat que obrigatoriamente aplica rate limit
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
      -X POST "${BASE_URL}/portal/test-chat" \
      -H "Authorization: Bearer ${API_KEY}" \
      -H "Content-Type: application/json" \
      -d "{\"model\": \"${MODEL_ID}\", \"prompt\": \"ok\", \"max_tokens\": 5}")
    STATUSES+=("${STATUS}")
    log_info "Request $i: HTTP ${STATUS}"
    sleep 0.1
done

# 5. Validar resultados
HAS_200=false
HAS_429=false
for s in "${STATUSES[@]}"; do
    if [[ "${s}" == "200" ]]; then HAS_200=true; fi
    if [[ "${s}" == "429" ]]; then HAS_429=true; fi
done

# 6. Verificar saúde do sistema
log_info "Verificando se o sistema continua healthy..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/health")

if [[ "${HAS_200}" == "true" && "${HAS_429}" == "true" && "${HEALTH_STATUS}" == "200" ]]; then
    log_ok "Rate limit comprovado com sucesso (200 OK e 429 Too Many Requests detectados)"
    echo "evidence=Rate limit detectado: statuses=${STATUSES[*]}"
    exit 0
else
    log_error "Falha na prova de rate limit."
    log_error "Statuses recebidos: ${STATUSES[*]}"
    log_error "Health check: ${HEALTH_STATUS}"
    
    if [[ "${HAS_429}" == "false" ]]; then
        log_warn "HINT: Rate limit pode estar desabilitado no servidor ou Redis não configurado."
    fi
    exit 1
fi

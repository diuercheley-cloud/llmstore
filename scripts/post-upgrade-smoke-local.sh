#!/usr/bin/env bash
set -euo pipefail

# scripts/post-upgrade-smoke-local.sh
# Post-upgrade/rollback smoke test for llm-inference-stack local.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

# Defaults
BASE_URL="${BASE_URL:-$(default_base_url)}"
SKIP_RAG=false
SKIP_TTS=false
SKIP_LMSTUDIO=true # Default to skip as it's often offline
OUTPUT_DIR="${ROOT_DIR}/artifacts/post-upgrade-smoke"
JSON_OUTPUT=false

usage() {
  cat <<EOF
Uso: $0 [OPÇÕES]

Opções:
  --base-url URL      URL base da stack (padrão: ${BASE_URL})
  --skip-rag          Pula testes de RAG
  --skip-tts          Pula testes de TTS
  --skip-lmstudio     Pula testes de LM Studio (padrão se não informado)
  --run-lmstudio      Executa testes de LM Studio
  --json              Gera apenas saída JSON no stdout
  --output-dir DIR    Diretório para artefatos (padrão: artifacts/post-upgrade-smoke)
  --help              Mostra esta mensagem

Este script valida rapidamente se a stack está funcional após um upgrade ou rollback.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url) BASE_URL="$2"; shift ;;
    --skip-rag) SKIP_RAG=true ;;
    --skip-tts) SKIP_TTS=true ;;
    --skip-lmstudio) SKIP_LMSTUDIO=true ;;
    --run-lmstudio) SKIP_LMSTUDIO=false ;;
    --json) JSON_OUTPUT=true ;;
    --output-dir) OUTPUT_DIR="$2"; shift ;;
    --help) usage; exit 0 ;;
    *) echo "Erro: Argumento desconhecido $1"; usage; exit 1 ;;
  esac
  shift
done

TIMESTAMP="$(date +%Y%m%dT%H%M%S)"
RUN_DIR="${OUTPUT_DIR}/${TIMESTAMP}"
LOG_DIR="${RUN_DIR}/logs"

mkdir -p "${LOG_DIR}"

# Credentials
DEMO_ENV="${ROOT_DIR}/.local/demo-client.env"
API_KEY=""
if [[ -f "${DEMO_ENV}" ]]; then
  API_KEY="$(grep DEMO_API_KEY "${DEMO_ENV}" | cut -d= -f2)"
fi

# If no API key found, we might need to use a dummy or fail if strict
# For smoke, we'll try to find any key if ADMIN_TOKEN is available
if [[ -z "${API_KEY}" ]] && [[ -n "${ADMIN_TOKEN:-}" ]]; then
  API_KEY="$(require_api_key "${BASE_URL}" "post-upgrade-smoke" || true)"
fi

# Test state
RESULTS_FILE="${RUN_DIR}/results.json"
REPORT_MD="${RUN_DIR}/smoke-report.md"
REPORT_JSON="${RUN_DIR}/smoke-report.json"

START_TIME=$(date +%s)

log_test() {
  local name="$1"
  local status="$2"
  local details="$3"
  
  if [[ "${JSON_OUTPUT}" == "false" ]]; then
    printf "[%-20s] %s\n" "${name}" "${status}"
  fi
  
  # Append to a temporary results file
  echo "{\"name\": \"${name}\", \"status\": \"${status}\", \"details\": \"${details//\"/\\\"}\"}" >> "${RUN_DIR}/raw_results.json"
}

check_endpoint() {
  local name="$1"
  local method="$2"
  local path="$3"
  local expected_code="$4"
  shift 4
  local extra_args=("$@")
  
  local log_file="${LOG_DIR}/${name}.log"
  local http_code
  
  http_code=$(curl_base_url "${BASE_URL}${path}" -s -o "${log_file}" -w "%{http_code}" -X "${method}" "${extra_args[@]}" || echo "000")
  
  if [[ "${http_code}" == "${expected_code}" ]]; then
    log_test "${name}" "PASS" "HTTP ${http_code}"
    return 0
  else
    log_test "${name}" "FAIL" "HTTP ${http_code} (esperado: ${expected_code})"
    return 1
  fi
}

# Ensure RUN_DIR exists
mkdir -p "${RUN_DIR}"
touch "${RUN_DIR}/raw_results.json"

if [[ "${JSON_OUTPUT}" == "false" ]]; then
  echo "--- Iniciando Post-Upgrade Smoke Test: ${TIMESTAMP} ---"
  echo "Base URL: ${BASE_URL}"
fi

set +e

# 1. Basic Health
check_endpoint "health" "GET" "/health" "200"
check_endpoint "ready" "GET" "/ready" "200"
check_endpoint "metrics" "GET" "/metrics" "200"

# 1.1 Migrations Status
if [[ -x "./scripts/validate-migrations-local.sh" ]]; then
  if ./scripts/validate-migrations-local.sh > "${LOG_DIR}/migrations-val.log" 2>&1; then
      log_test "migrations_status" "PASS" "Alembic migrations OK"
  else
      log_test "migrations_status" "FAIL" "Alembic migrations com erro (veja logs/migrations-val.log)"
  fi
else
  log_test "migrations_status" "SKIP" "Script de validação não encontrado"
fi

# 2. Docker Status
if [[ "${JSON_OUTPUT}" == "false" ]]; then
  docker compose ps > "${LOG_DIR}/docker-ps.log" 2>&1
fi
if dc ps | grep -q "Exit"; then
  log_test "docker_ps" "FAIL" "Existem containers com erro"
else
  log_test "docker_ps" "PASS" "Todos containers OK"
fi

# 3. Admin Health
if [[ -n "${ADMIN_TOKEN:-}" ]]; then
  check_endpoint "admin_health_deep" "GET" "/admin/health/deep" "200" -H "X-Admin-Token: ${ADMIN_TOKEN}"
  check_endpoint "admin_billing_plans" "GET" "/admin/billing/plans" "200" -H "X-Admin-Token: ${ADMIN_TOKEN}"
else
  log_test "admin_checks" "SKIP" "ADMIN_TOKEN não definido"
fi

# 4. Inference
if [[ -n "${API_KEY}" ]]; then
  check_endpoint "v1_models" "GET" "/v1/models" "200" -H "Authorization: Bearer ${API_KEY}"
  
  # Chat Completion Simple
  check_endpoint "chat_completion" "POST" "/v1/chat/completions" "200" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"model": "default", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 5}'

  # Streaming Simple
  check_endpoint "chat_stream" "POST" "/v1/chat/completions" "200" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"model": "default", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 5, "stream": true}'
else
  log_test "inference_checks" "FAIL" "API_KEY não encontrada (rode seed-demo-local.sh)"
fi

# 5. RAG
if [[ "${SKIP_RAG}" == "false" ]]; then
  if [[ -n "${API_KEY}" ]]; then
    # We check if RAG is available by querying status or attempting a query
    # Using /admin/tests/rag/status if possible
    if [[ -n "${ADMIN_TOKEN:-}" ]]; then
       check_endpoint "rag_status" "GET" "/admin/tests/rag/status" "200" -H "X-Admin-Token: ${ADMIN_TOKEN}"
    fi
    # Attempt a simple query (might return 404 if no docs, but we want to see if the endpoint exists)
    check_endpoint "rag_query" "POST" "/client/rag/query" "200" \
      -H "Authorization: Bearer ${API_KEY}" \
      -H "Content-Type: application/json" \
      -d '{"query": "test", "stream": false}' || true
  else
    log_test "rag_checks" "SKIP" "API_KEY ausente"
  fi
else
  log_test "rag_checks" "SKIP" "Ignorado via flag"
fi

# 6. TTS
if [[ "${SKIP_TTS}" == "false" ]]; then
  # TTS health
  check_endpoint "tts_health" "GET" "/pocket-tts/health" "200" || log_test "tts_health" "WARN" "TTS Offline"
  
  # TTS generation (short)
  curl_base_url "${BASE_URL}/pocket-tts/tts" -s -o "${LOG_DIR}/tts_gen.wav" -w "%{http_code}" -X POST \
    -F "text=smoke test" > "${LOG_DIR}/tts_gen_code.log"
  TTS_CODE=$(cat "${LOG_DIR}/tts_gen_code.log")
  if [[ "${TTS_CODE}" == "200" ]]; then
    log_test "tts_gen" "PASS" "Áudio gerado"
  else
    log_test "tts_gen" "WARN" "Falha ao gerar áudio (HTTP ${TTS_CODE})"
  fi
else
  log_test "tts_gen" "SKIP" "Ignorado via flag"
fi

# 7. Security Score
LATEST_SEC_REPORT=$(find artifacts/security-reports -name "report.json" -type f | sort -r | head -n 1 || echo "")
if [[ -n "${LATEST_SEC_REPORT}" ]]; then
  SEC_SCORE=$(python3 -c "import json; print(json.load(open('${LATEST_SEC_REPORT}'))['summary']['score'])" 2>/dev/null || echo "N/A")
  log_test "security_score" "INFO" "Último score: ${SEC_SCORE}"
else
  log_test "security_score" "SKIP" "Nenhum relatório encontrado"
fi

set -e

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Generate Reports
RESULTS_JSON_LIST=$(cat "${RUN_DIR}/raw_results.json" | python3 -c 'import json, sys; print(json.dumps([json.loads(line) for line in sys.stdin]))')
rm "${RUN_DIR}/raw_results.json"

cat <<EOF > "${REPORT_JSON}"
{
  "timestamp": "${TIMESTAMP}",
  "duration_seconds": ${DURATION},
  "base_url": "${BASE_URL}",
  "results": ${RESULTS_JSON_LIST}
}
EOF

# Markdown Report
{
  echo "# Smoke Test Report - ${TIMESTAMP}"
  echo ""
  echo "- **Data:** $(date)"
  echo "- **Base URL:** ${BASE_URL}"
  echo "- **Duração:** ${DURATION}s"
  echo ""
  echo "## Resultados"
  echo ""
  echo "| Teste | Status | Detalhes |"
  echo "|-------|--------|----------|"
  echo "${RESULTS_JSON_LIST}" | python3 -c "import json, sys; data=json.load(sys.stdin); [print(f'| {r[\"name\"]} | {r[\"status\"]} | {r[\"details\"]} |') for r in data]"
} > "${REPORT_MD}"

if [[ "${JSON_OUTPUT}" == "true" ]]; then
  cat "${REPORT_JSON}"
else
  echo ""
  
  # Exit with error if any PASS failed (excluding WARN/SKIP/INFO)
  if echo "${RESULTS_JSON_LIST}" | python3 -c "import json, sys; data=json.load(sys.stdin); sys.exit(1 if any(r['status'] == 'FAIL' for r in data) else 0)"; then
    operator_success "Smoke test da stack concluído com sucesso!"
    add_next_step "Relatório completo em: ${REPORT_MD}"
    print_next_steps
    exit 0
  else
    operator_error "HEALTH_FAILED" "O smoke test identificou falhas na stack." "Revise os logs detalhados e o relatório em ${REPORT_MD}" "Um ou mais testes falharam com status FAIL."
    add_next_step "Relatório completo em: ${REPORT_MD}"
    print_next_steps
    exit 1
  fi
fi

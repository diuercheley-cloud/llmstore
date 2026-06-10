#!/usr/bin/env bash
# scripts/validators/generate-client-monthly-report.sh
# Generates a local monthly usage report for a client.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

CLIENT_ID=""
EMAIL=""
MONTH=""
OUTPUT_DIR="${ROOT_DIR}/artifacts/monthly-reports"
INCLUDE_TECHNICAL_DETAILS=false

show_help() {
    cat <<EOF
Usage: $0 [options]

Options:
  --client-id UUID           Client UUID (fetches data from API)
  --email EMAIL              Client email for identification
  --month YYYY-MM            (Required) Report month
  --output-dir DIR           Output directory. Default: artifacts/monthly-reports
  --include-technical-details  Include technical plan/quota details
  --help                     Show this help

Generates:
  artifacts/monthly-reports/<client>/<month>/monthly-report.json
  artifacts/monthly-reports/<client>/<month>/monthly-report.md
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --client-id) CLIENT_ID="$2"; shift 2 ;;
        --email) EMAIL="$2"; shift 2 ;;
        --month) MONTH="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --include-technical-details) INCLUDE_TECHNICAL_DETAILS=true; shift ;;
        --help) show_help ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
done

if [[ -z "${MONTH}" ]]; then
    echo "Error: --month YYYY-MM is required"
    exit 1
fi

if ! echo "${MONTH}" | grep -qE '^[0-9]{4}-(0[1-9]|1[0-2])$'; then
    echo "Error: Invalid month format. Use YYYY-MM (e.g. 2026-05)"
    exit 1
fi

YEAR="${MONTH%-*}"
MONTH_NUM="${MONTH#*-}"
MONTH_NUM_INT=$((10#${MONTH_NUM}))
CLIENT_LABEL="${CLIENT_ID:-${EMAIL:-unknown}}"
SAFE_CLIENT=$(echo "${CLIENT_LABEL}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
[[ -z "${SAFE_CLIENT}" ]] && SAFE_CLIENT="unknown"

REPORT_DIR="${OUTPUT_DIR}/${SAFE_CLIENT}/${MONTH}"
mkdir -p "${REPORT_DIR}"

JSON_FILE="${REPORT_DIR}/monthly-report.json"
MD_FILE="${REPORT_DIR}/monthly-report.md"

TIMESTAMP=$(date +%Y%m%dT%H%M%S)
DATE_STR=$(date "+%Y-%m-%d")

# Build report data
# Try to fetch from admin API if client-id provided and server is running
API_DATA="{}"
ADMIN_TOKEN=""
# Attempt to read admin token from .env.local
if [[ -f "${ROOT_DIR}/.env.local" ]]; then
    ADMIN_TOKEN=$(grep -E '^ADMIN_TOKEN=' "${ROOT_DIR}/.env.local" | cut -d= -f2- | tr -d '"'"'" || true)
fi
if [[ -z "${ADMIN_TOKEN}" && -f "${ROOT_DIR}/.env" ]]; then
    ADMIN_TOKEN=$(grep -E '^ADMIN_TOKEN=' "${ROOT_DIR}/.env" | cut -d= -f2- | tr -d '"'"'" || true)
fi

if [[ -n "${CLIENT_ID}" && -n "${ADMIN_TOKEN}" ]]; then
    API_BASE="${API_BASE:-http://localhost:18080}"
    TECH_PARAM=""
    ${INCLUDE_TECHNICAL_DETAILS} && TECH_PARAM="&include_technical_details=true"
    CURL_OUT=$(curl -sf "${API_BASE}/admin/sales/monthly-report-preview?client_id=${CLIENT_ID}&month=${MONTH}${TECH_PARAM}" \
        -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null || true)
    if [[ -n "${CURL_OUT}" ]]; then
        API_DATA="${CURL_OUT}"
    fi
fi

# Extract data from API response or use defaults
CLIENT_NAME=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('client',{}).get('name','${CLIENT_LABEL}'))" 2>/dev/null || echo "${CLIENT_LABEL}")
PLAN_CODE=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('client',{}).get('plan_code','N/A'))" 2>/dev/null || echo "N/A")
PLAN_NAME=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('client',{}).get('plan_name','N/A'))" 2>/dev/null || echo "N/A")
BILLING_STATUS=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('client',{}).get('billing_status','active'))" 2>/dev/null || echo "active")

TOKENS=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('usage',{}).get('chat',{}).get('total_tokens',0))" 2>/dev/null || echo "0")
REQUESTS=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('usage',{}).get('chat',{}).get('requests',0))" 2>/dev/null || echo "0")
ERRORS=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('usage',{}).get('errors',{}).get('total',0))" 2>/dev/null || echo "0")
RATE_LIMIT=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('usage',{}).get('errors',{}).get('rate_limit_events',0))" 2>/dev/null || echo "0")

EMBEDDINGS_REQ=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('usage',{}).get('embeddings',{}).get('requests',0))" 2>/dev/null || echo "0")
EMBEDDINGS_TOK=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('usage',{}).get('embeddings',{}).get('tokens',0))" 2>/dev/null || echo "0")
RAG_QUERIES=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('usage',{}).get('rag',{}).get('queries',0))" 2>/dev/null || echo "0")
RAG_DOCS=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('usage',{}).get('rag',{}).get('documents',0))" 2>/dev/null || echo "0")
TTS_CHARS=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('usage',{}).get('tts',{}).get('chars',0))" 2>/dev/null || echo "0")
RESPONSES=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('usage',{}).get('responses',0))" 2>/dev/null || echo "0")
LATENCY=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('usage',{}).get('performance',{}).get('avg_latency_ms',0))" 2>/dev/null || echo "0")

TOTAL_BILLED=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('billing',{}).get('totals',{}).get('billed',0))" 2>/dev/null || echo "0")
TOTAL_PAID=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('billing',{}).get('totals',{}).get('paid',0))" 2>/dev/null || echo "0")
TOTAL_PENDING=$(echo "${API_DATA}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('billing',{}).get('totals',{}).get('pending',0))" 2>/dev/null || echo "0")

RECOMMENDATIONS_JSON=$(echo "${API_DATA}" | python3 -c "
import sys, json
d = json.load(sys.stdin)
recs = d.get('recommendations', [])
print(json.dumps(recs))
" 2>/dev/null || echo '[]')

RECOMMENDATIONS_MD=$(echo "${RECOMMENDATIONS_JSON}" | python3 -c "
import sys, json
recs = json.load(sys.stdin)
if not recs:
    print('- Nenhuma recomendação no momento.')
else:
    for r in recs:
        print(f\"- **{r.get('type','').upper()}:** {r.get('reason','')}\")
" 2>/dev/null || echo "- Nenhuma recomendação disponível.")

# Generate JSON
cat <<EOF > "${JSON_FILE}"
{
  "report_version": "1.0",
  "generated_at": "${TIMESTAMP}",
  "generated_date": "${DATE_STR}",
  "client": {
    "id": "${CLIENT_ID}",
    "name": "${CLIENT_NAME}",
    "email": "${EMAIL}",
    "plan_code": "${PLAN_CODE}",
    "plan_name": "${PLAN_NAME}",
    "billing_status": "${BILLING_STATUS}"
  },
  "period": {
    "month": "${MONTH}",
    "year": ${YEAR},
    "month_num": ${MONTH_NUM_INT}
  },
  "usage": {
    "chat_tokens": ${TOKENS},
    "requests": ${REQUESTS},
    "responses": ${RESPONSES},
    "embeddings_requests": ${EMBEDDINGS_REQ},
    "embeddings_tokens": ${EMBEDDINGS_TOK},
    "rag_queries": ${RAG_QUERIES},
    "rag_documents": ${RAG_DOCS},
    "tts_chars": ${TTS_CHARS},
    "errors": ${ERRORS},
    "rate_limit_events": ${RATE_LIMIT},
    "avg_latency_ms": ${LATENCY}
  },
  "billing": {
    "total_billed": ${TOTAL_BILLED},
    "total_paid": ${TOTAL_PAID},
    "total_pending": ${TOTAL_PENDING},
    "payment_status": "${BILLING_STATUS}"
  },
  "recommendations": ${RECOMMENDATIONS_JSON}
}
EOF

# Re-read the full API data for the MD report
API_DATA_FORMATTED=""
if [[ "${API_DATA}" != "{}" ]]; then
    API_DATA_FORMATTED=$(echo "${API_DATA}" | python3 -m json.tool 2>/dev/null || echo "${API_DATA}")
fi

# Generate Markdown
cat <<MDEOF > "${MD_FILE}"
# Relatório Mensal de Uso — ${CLIENT_NAME}

**Mês:** ${MONTH}  
**Cliente:** ${CLIENT_NAME} (${EMAIL})  
**Plano:** ${PLAN_NAME} (${PLAN_CODE})  
**Status de Pagamento:** ${BILLING_STATUS}  
**Gerado em:** ${DATE_STR}

---

## Resumo de Consumo

| Métrica | Valor | Limite Mensal |
|---------|-------|---------------|
| Tokens de Chat (total) | ${TOKENS} | — |
| Requests | ${REQUESTS} | — |
| Responses | ${RESPONSES} | — |
| Embeddings (requests) | ${EMBEDDINGS_REQ} | — |
| Embeddings (tokens) | ${EMBEDDINGS_TOK} | — |
| RAG (queries) | ${RAG_QUERIES} | — |
| TTS (chars) | ${TTS_CHARS} | — |
| Erros | ${ERRORS} | — |
| Rate Limit Events | ${RATE_LIMIT} | — |
| Latência Média | ${LATENCY} ms | — |

## Faturamento Local / Manual

| Item | Valor |
|------|-------|
| Total Faturado (mês) | ${TOTAL_BILLED} |
| Total Pago | ${TOTAL_PAID} |
| Total Pendente | ${TOTAL_PENDING} |
| Status de Pagamento | ${BILLING_STATUS} |

> **AVISO:** Este sistema não processa pagamentos reais via PSP ou PIX. O faturamento é local/manual para referência.

## Recomendações

${RECOMMENDATIONS_MD}

---

## Upgrade / Downgrade Sugerido

Com base no consumo de **${TOKENS} tokens** no período:

MDEOF

# Add upgrade/downgrade suggestion
if command -v python3 &>/dev/null; then
    python3 -c "
tokens = ${TOKENS}
if tokens < 1000000:
    print('Plano atual parece adequado para o volume. Se o padrão se mantiver, um plano de menor custo pode ser avaliado.')
elif tokens < 10000000:
    print('Consumo moderado. Verifique se o plano atual atende à projeção de crescimento.')
else:
    print('Consumo elevado. Considere upgrade de plano para garantir recursos e suporte adequados.')
" >> "${MD_FILE}"
fi

cat <<MDEOF >> "${MD_FILE}"

## Limitações

- Este relatório é gerado localmente para referência do cliente.
- Não há processamento de pagamentos reais via PSP ou PIX.
- Valores de faturamento são simulações locais.
- Não substitui documentos fiscais oficiais.
- Dados de uso são baseados em logs locais e podem ter atraso de até 24h.

---

*Relatório gerado automaticamente em ${DATE_STR} às ${TIMESTAMP}*  
*LLM Inference Stack — Monthly Report v1.0*
MDEOF

echo "Monthly report generated successfully:"
echo "  JSON: ${JSON_FILE}"
echo "  Markdown: ${MD_FILE}"

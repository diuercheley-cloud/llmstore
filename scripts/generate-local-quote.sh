#!/usr/bin/env bash
# scripts/generate-local-quote.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PRICING_CONFIG="${ROOT_DIR}/config/pricing.local.json"

if [[ ! -f "${PRICING_CONFIG}" ]]; then
  PRICING_CONFIG="${ROOT_DIR}/config/pricing.example.json"
fi

COMPANY_NAME=""
PLAN="Basic"
USERS=0
MODELS=1
RAG=false
TTS=false
EMBEDDINGS=false
RESPONSES=0
SUPPORT_HOURS=0
CUSTOM_INTEGRATION_HOURS=0
DISCOUNT_PERCENT=0
OUTPUT_DIR="${ROOT_DIR}/artifacts/quotes"

show_help() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --company-name NAME"
  echo "  --plan PLAN (Free|Basic|Pro|Enterprise Local)"
  echo "  --users NUMBER"
  echo "  --models NUMBER"
  echo "  --rag"
  echo "  --tts"
  echo "  --embeddings"
  echo "  --responses NUMBER"
  echo "  --support-hours NUMBER"
  echo "  --custom-integration-hours NUMBER"
  echo "  --discount-percent NUMBER"
  echo "  --output-dir DIR"
  echo "  --help"
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --company-name) COMPANY_NAME="$2"; shift 2 ;;
    --plan) PLAN="$2"; shift 2 ;;
    --users) USERS="$2"; shift 2 ;;
    --models) MODELS="$2"; shift 2 ;;
    --rag) RAG=true; shift ;;
    --tts) TTS=true; shift ;;
    --embeddings) EMBEDDINGS=true; shift ;;
    --responses) RESPONSES="$2"; shift 2 ;;
    --support-hours) SUPPORT_HOURS="$2"; shift 2 ;;
    --custom-integration-hours) CUSTOM_INTEGRATION_HOURS="$2"; shift 2 ;;
    --discount-percent) DISCOUNT_PERCENT="$2"; shift 2 ;;
    --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --help) show_help; exit 0 ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
done

if [[ -z "${COMPANY_NAME}" ]]; then
  echo "Error: --company-name is required"
  exit 1
fi

# Load pricing
CURRENCY=$(jq -r '.currency' "${PRICING_CONFIG}")
SETUP_FEE=$(jq -r ".setup_fee_by_plan[\"${PLAN}\"] // 0" "${PRICING_CONFIG}")
MONTHLY_FEE=$(jq -r ".monthly_fee_by_plan[\"${PLAN}\"] // 0" "${PRICING_CONFIG}")
SUPPORT_RATE=$(jq -r '.support_hour_rate' "${PRICING_CONFIG}")
RAG_SETUP_FEE=$(jq -r '.rag_setup_fee' "${PRICING_CONFIG}")
TTS_SETUP_FEE=$(jq -r '.tts_setup_fee' "${PRICING_CONFIG}")
CUSTOM_INT_RATE=$(jq -r '.custom_integration_hour_rate' "${PRICING_CONFIG}")

# Calculations
TOTAL_SETUP=0
TOTAL_SETUP=$((TOTAL_SETUP + SETUP_FEE))

if [[ "$RAG" == true ]]; then
  TOTAL_SETUP=$((TOTAL_SETUP + RAG_SETUP_FEE))
fi

if [[ "$TTS" == true ]]; then
  TOTAL_SETUP=$((TOTAL_SETUP + TTS_SETUP_FEE))
fi

CUSTOM_INT_COST=$((CUSTOM_INTEGRATION_HOURS * CUSTOM_INT_RATE))
TOTAL_SETUP=$((TOTAL_SETUP + CUSTOM_INT_COST))

MONTHLY_SUPPORT_COST=$((SUPPORT_HOURS * SUPPORT_RATE))
TOTAL_RECURRING=$((MONTHLY_FEE + MONTHLY_SUPPORT_COST))

TOTAL_FIRST_MONTH=$((TOTAL_SETUP + TOTAL_RECURRING))

# Apply discount
DISCOUNT_AMOUNT=$(echo "scale=0; ${TOTAL_FIRST_MONTH} * ${DISCOUNT_PERCENT} / 100" | bc)
TOTAL_FIRST_MONTH_DISCOUNTED=$(echo "${TOTAL_FIRST_MONTH} - ${DISCOUNT_AMOUNT}" | bc)

TIMESTAMP=$(date +%Y%m%dT%H%M%S)
SAFE_COMPANY=$(echo "${COMPANY_NAME}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g')
QUOTE_DIR="${OUTPUT_DIR}/${TIMESTAMP}"
mkdir -p "${QUOTE_DIR}"

JSON_FILE="${QUOTE_DIR}/${SAFE_COMPANY}-quote.json"
MD_FILE="${QUOTE_DIR}/${SAFE_COMPANY}-quote.md"

# Generate JSON
cat <<EOF > "${JSON_FILE}"
{
  "company_name": "${COMPANY_NAME}",
  "plan": "${PLAN}",
  "currency": "${CURRENCY}",
  "details": {
    "setup_fee": ${SETUP_FEE},
    "rag_setup": $([[ "$RAG" == true ]] && echo "${RAG_SETUP_FEE}" || echo 0),
    "tts_setup": $([[ "$TTS" == true ]] && echo "${TTS_SETUP_FEE}" || echo 0),
    "custom_integration_hours": ${CUSTOM_INTEGRATION_HOURS},
    "custom_integration_cost": ${CUSTOM_INT_COST},
    "monthly_base": ${MONTHLY_FEE},
    "support_hours": ${SUPPORT_HOURS},
    "support_cost": ${MONTHLY_SUPPORT_COST}
  },
  "totals": {
    "setup": ${TOTAL_SETUP},
    "recurring": ${TOTAL_RECURRING},
    "first_month_total": ${TOTAL_FIRST_MONTH},
    "discount_percent": ${DISCOUNT_PERCENT},
    "discount_amount": ${DISCOUNT_AMOUNT},
    "first_month_final": ${TOTAL_FIRST_MONTH_DISCOUNTED}
  },
  "validity_days": 15,
  "timestamp": "${TIMESTAMP}"
}
EOF

# Generate Markdown
cat <<EOF > "${MD_FILE}"
# Orçamento: ${COMPANY_NAME}
Data: $(date +%Y-%m-%d)
Validade: 15 dias

## Resumo do Plano
**Plano:** ${PLAN}
**Moeda:** ${CURRENCY}

## Detalhes de Investimento (Setup)
- Taxa de Implementação (${PLAN}): ${CURRENCY} ${SETUP_FEE}
$([[ "$RAG" == true ]] && echo "- Ativação RAG: ${CURRENCY} ${RAG_SETUP_FEE}")
$([[ "$TTS" == true ]] && echo "- Ativação TTS: ${CURRENCY} ${TTS_SETUP_FEE}")
$([[ ${CUSTOM_INTEGRATION_HOURS} -gt 0 ]] && echo "- Integração Customizada (${CUSTOM_INTEGRATION_HOURS}h): ${CURRENCY} ${CUSTOM_INT_COST}")
**Total Setup:** ${CURRENCY} ${TOTAL_SETUP}

## Custos Recorrentes (Mensais)
- Mensalidade ${PLAN}: ${CURRENCY} ${MONTHLY_FEE}
- Suporte (${SUPPORT_HOURS}h): ${CURRENCY} ${MONTHLY_SUPPORT_COST}
**Total Recorrente:** ${CURRENCY} ${TOTAL_RECURRING}

## Totais
- **Total Primeiro Mês:** ${CURRENCY} ${TOTAL_FIRST_MONTH}
- **Desconto (${DISCOUNT_PERCENT}%):** ${CURRENCY} ${DISCOUNT_AMOUNT}
- **Valor Final Primeiro Mês:** ${CURRENCY} ${TOTAL_FIRST_MONTH_DISCOUNTED}

---
### Observações
- Valores configuráveis localmente para fins de demonstração.
- Não inclui hardware ou infraestrutura de rede.
- Sujeito a alteração após análise técnica de escopo.

### Fora de Escopo
- Desenvolvimento de front-end personalizado.
- Integração com sistemas legados não documentados.
- Licenciamento de modelos proprietários de terceiros.

EOF

echo "Quote generated successfully:"
echo "JSON: ${JSON_FILE}"
echo "Markdown: ${MD_FILE}"

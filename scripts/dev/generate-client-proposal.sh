#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
source "${SCRIPT_DIR}/../dev/common.sh"

init_stack_env

# Default values
LEAD_ID=""
COMPANY_NAME=""
CONTACT_NAME=""
SEGMENT=""
PLAN="Basic"
SETUP_FEE=""
MONTHLY_FEE=""
CURRENCY="BRL"
OUTPUT_DIR="${ROOT_DIR}/artifacts/proposals"
FORMAT="md"
DRY_RUN=false
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
DATE_STR=$(date "+%d/%m/%Y")

# Load config
CONFIG_FILE="${ROOT_DIR}/config/sales-proposal.json"
if [ ! -f "$CONFIG_FILE" ]; then
    CONFIG_FILE="${ROOT_DIR}/config/sales-proposal.example.json"
fi

DEFAULT_CURRENCY=$(jq -r '.default_currency // "BRL"' "$CONFIG_FILE")
DEFAULT_SETUP_FEE=$(jq -r '.default_setup_fee // 5000' "$CONFIG_FILE")
DEFAULT_MONTHLY_FEE=$(jq -r '.default_monthly_fee // 2000' "$CONFIG_FILE")
DEFAULT_VALIDITY=$(jq -r '.default_validity_days // 15' "$CONFIG_FILE")
PROVIDER_NAME=$(jq -r '.provider_name // "Local AI Solutions"' "$CONFIG_FILE")
PROVIDER_CONTACT=$(jq -r '.provider_contact // "sales@local-ai.solutions"' "$CONFIG_FILE")

# Helper to show help
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --lead-id ID          Search lead data from CRM"
    echo "  --company-name NAME   Client company name"
    echo "  --contact-name NAME   Contact person name"
    echo "  --segment SEGMENT     Client segment"
    echo "  --plan PLAN           Recommended plan (Basic|Pro|Enterprise)"
    echo "  --setup-fee VALUE     Custom setup fee"
    echo "  --monthly-fee VALUE   Custom monthly fee"
    echo "  --currency CODE       Currency (default: BRL)"
    echo "  --output-dir DIR      Output directory"
    echo "  --format md|pdf       Output format"
    echo "  --dry-run             Do not save files"
    echo "  --help                Show this help"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --lead-id) LEAD_ID="$2"; shift 2 ;;
        --company-name) COMPANY_NAME="$2"; shift 2 ;;
        --contact-name) CONTACT_NAME="$2"; shift 2 ;;
        --segment) SEGMENT="$2"; shift 2 ;;
        --plan) PLAN="$2"; shift 2 ;;
        --setup-fee) SETUP_FEE="$2"; shift 2 ;;
        --monthly-fee) MONTHLY_FEE="$2"; shift 2 ;;
        --currency) CURRENCY="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --format) FORMAT="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        --help) show_help; exit 0 ;;
        *) echo "Unknown option: $1"; show_help; exit 1 ;;
    esac
done

# If lead-id is provided, fetch data
if [[ -n "$LEAD_ID" ]]; then
    echo "Fetching lead data for ID: $LEAD_ID..."
    BASE_URL="$(default_base_url)"
    ADMIN_TOKEN="${ADMIN_TOKEN:-super-secret-admin-token}"
    # Try to fetch lead data
    LEAD_JSON=$(curl -fsS "${BASE_URL}/admin/sales/leads/${LEAD_ID}" -H "X-Admin-Token: ${ADMIN_TOKEN}" 2>/dev/null || echo "{}")
    
    if [[ "$LEAD_JSON" != "{}" ]]; then
        COMPANY_NAME="${COMPANY_NAME:-$(echo "$LEAD_JSON" | jq -r '.company_name // empty')}"
        CONTACT_NAME="${CONTACT_NAME:-$(echo "$LEAD_JSON" | jq -r '.contact_name // empty')}"
        SEGMENT="${SEGMENT:-$(echo "$LEAD_JSON" | jq -r '.segment // empty')}"
    else
        echo "Warning: Lead not found or CRM unreachable. Using provided or default data."
    fi
fi

# Fallbacks
COMPANY_NAME="${COMPANY_NAME:-Cliente Exemplo}"
CONTACT_NAME="${CONTACT_NAME:-Responsável}"
SEGMENT="${SEGMENT:-Geral}"
SETUP_FEE="${SETUP_FEE:-$DEFAULT_SETUP_FEE}"
MONTHLY_FEE="${MONTHLY_FEE:-$DEFAULT_MONTHLY_FEE}"
CURRENCY="${CURRENCY:-$DEFAULT_CURRENCY}"

SAFE_COMPANY_NAME=$(echo "$COMPANY_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
PROPOSAL_DIR="${OUTPUT_DIR}/${TIMESTAMP}"
PROPOSAL_FILE="${PROPOSAL_DIR}/${SAFE_COMPANY_NAME}-proposal.md"
METADATA_FILE="${PROPOSAL_DIR}/proposal-metadata.json"

if [[ "$DRY_RUN" == "true" ]]; then
    echo "Dry run: Proposal would be generated for $COMPANY_NAME"
    exit 0
fi

mkdir -p "$PROPOSAL_DIR"

# Generate Metadata
cat <<EOF > "$METADATA_FILE"
{
  "lead_id": "$LEAD_ID",
  "company_name": "$COMPANY_NAME",
  "contact_name": "$CONTACT_NAME",
  "segment": "$SEGMENT",
  "plan": "$PLAN",
  "setup_fee": $SETUP_FEE,
  "monthly_fee": $MONTHLY_FEE,
  "currency": "$CURRENCY",
  "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "validity_days": $DEFAULT_VALIDITY
}
EOF

# Generate Proposal Markdown
cat <<EOF > "$PROPOSAL_FILE"
# Proposta Comercial: llm-inference-stack

**Cliente:** $COMPANY_NAME
**Aos cuidados de:** $CONTACT_NAME
**Data:** $DATE_STR
**Validade:** $DEFAULT_VALIDITY dias
**Consultor:** $PROVIDER_NAME ($PROVIDER_CONTACT)

---

## 1. Capa
Esta proposta detalha a implementação do **llm-inference-stack**, uma solução de IA Generativa local, segura e escalável, personalizada para o segmento de **$SEGMENT**.

## 2. Diagnóstico do Problema
Identificamos que a $COMPANY_NAME busca:
- Eliminar riscos de privacidade associados a LLMs em nuvem pública.
- Controlar custos operacionais com previsibilidade total.
- Acelerar a adoção de IA com uma infraestrutura pronta para uso (Appliance).

## 3. Solução Proposta
A implementação do **Local AI Appliance**, provendo:
- API compatível com OpenAI rodando internamente.
- Suporte a RAG (Retrieval-Augmented Generation) para documentos internos.
- Painel de controle para gestão de cotas e usuários.

## 4. Arquitetura Local
A solução será instalada on-premise, garantindo que **nenhum dado saia da rede da $COMPANY_NAME**. 
Utilizamos containers Docker para orquestração dos modelos e base de conhecimento vetorial.

## 5. Escopo
$(jq -r '.default_scope[] | "- " + .' "$CONFIG_FILE")

## 6. Fora do Escopo
$(jq -r '.exclusions[] | "- " + .' "$CONFIG_FILE")
- **Atenção:** Esta solução não inclui processamento real de pagamentos (PSP/PIX). O faturamento é manual e local.

## 7. Plano Recomendado: $PLAN
O plano **$PLAN** oferece o equilíbrio ideal entre performance e custo para o volume projetado.

## 8. Valores (em $CURRENCY)
- **Setup Único:** $CURRENCY $SETUP_FEE
- **Mensalidade:** $CURRENCY $MONTHLY_FEE
- **Suporte:** $(jq -r '.default_support_hours' "$CONFIG_FILE")

## 9. Cronograma
- Semana 1: Diagnóstico e preparação de ambiente.
- Semana 2: Instalação e configuração inicial.
- Semana 3: Integração de dados (RAG) e testes.
- Semana 4: Treinamento e Go-live.

## 10. Responsabilidades do Cliente
- Prover hardware compatível (GPU recomendada).
- Disponibilizar acesso técnico ao ambiente de instalação.
- Fornecer documentação para a base de conhecimento (RAG).

## 11. Responsabilidades do Fornecedor
- Garantir a estabilidade da pilha tecnológica.
- Prover atualizações de segurança e performance.
- Oferecer suporte técnico conforme acordado.

## 12. Critérios de Aceite
- API respondendo a requisições de chat.
- Base de conhecimento retornando informações relevantes via RAG.
- Painel administrativo acessível e funcional.

## 13. Validade da Proposta
Esta proposta é válida por $DEFAULT_VALIDITY dias a partir desta data.

## 14. Próximos Passos
1. Aprovação formal desta proposta.
2. Assinatura do contrato de prestação de serviços.
3. Reunião de Kick-off técnico.

---
**$PROVIDER_NAME**
$PROVIDER_CONTACT
EOF

echo "Proposal generated successfully at: $PROPOSAL_FILE"
echo "Metadata saved at: $METADATA_FILE"

# Optional PDF generation
if [[ "$FORMAT" == "pdf" ]]; then
    if [[ -f "${SCRIPT_DIR}/../legacy/generate-proposal-pdf.sh" ]]; then
        echo "Generating PDF..."
        "${SCRIPT_DIR}/../legacy/generate-proposal-pdf.sh" "$PROPOSAL_FILE" || echo "Warning: PDF generation failed."
    else
        echo "Skip: scripts/legacy/generate-proposal-pdf.sh not found. PDF not generated."
    fi
fi

# Optional CRM Integration: Record artifact in lead history
if [[ -n "$LEAD_ID" ]]; then
    echo "Recording proposal in CRM for lead $LEAD_ID..."
    BASE_URL="$(default_base_url)"
    curl -fsS -X POST "${BASE_URL}/admin/sales/leads/${LEAD_ID}/notes" \
      -H "X-Admin-Token: ${ADMIN_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{\"content\": \"Proposta gerada automaticamente: $(basename "$PROPOSAL_FILE")\"}" > /dev/null || echo "Warning: Failed to record note in CRM."
fi

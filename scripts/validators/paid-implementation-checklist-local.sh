#!/usr/bin/env bash
# scripts/validators/paid-implementation-checklist-local.sh
# Generates a paid implementation checklist for a client deployment.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
TEMPLATE="${ROOT_DIR}/docs/PAID_IMPLEMENTATION_CHECKLIST.md"

COMPANY_NAME=""
OPERATOR_NAME=""
OUTPUT_DIR="${ROOT_DIR}/artifacts/implementation-checklists"

show_help() {
    cat <<EOF
Usage: $0 [options]

Options:
  --company-name NAME   (Required) Client company name
  --operator-name NAME  (Required) Operator/provider name
  --output-dir DIR      Output directory. Default: artifacts/implementation-checklists
  --help                Show this help

Generates:
  artifacts/implementation-checklists/<timestamp>/implementation-checklist.md
  artifacts/implementation-checklists/<timestamp>/implementation-checklist.json
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --company-name) COMPANY_NAME="$2"; shift 2 ;;
        --operator-name) OPERATOR_NAME="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --help) show_help ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
done

if [[ -z "${COMPANY_NAME}" ]] || [[ -z "${OPERATOR_NAME}" ]]; then
    echo "Error: --company-name and --operator-name are required"
    exit 1
fi

if [[ ! -f "${TEMPLATE}" ]]; then
    echo "Error: Template not found at ${TEMPLATE}"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%dT%H%M%S)
SAFE_COMPANY=$(echo "${COMPANY_NAME}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g')
OUTPUT_DIR_FULL="${OUTPUT_DIR}/${TIMESTAMP}"
mkdir -p "${OUTPUT_DIR_FULL}"

MD_FILE="${OUTPUT_DIR_FULL}/implementation-checklist.md"
JSON_FILE="${OUTPUT_DIR_FULL}/implementation-checklist.json"
DATE_STR=$(date "+%Y-%m-%d")

# Generate Markdown by substituting placeholders
sed \
    -e "s/___________________________________________________/${COMPANY_NAME}/" \
    -e "s/________________________________________________/${OPERATOR_NAME}/" \
    -e "s/__________________/${DATE_STR}/" \
    -e "s/{{DATE}}/${DATE_STR}/g" \
    "${TEMPLATE}" > "${MD_FILE}"

# Generate JSON metadata
cat <<EOF > "${JSON_FILE}"
{
  "template": "PAID_IMPLEMENTATION_CHECKLIST.md",
  "company_name": "${COMPANY_NAME}",
  "operator_name": "${OPERATOR_NAME}",
  "generated_at": "${TIMESTAMP}",
  "date": "${DATE_STR}",
  "output_dir": "${OUTPUT_DIR_FULL}",
  "status": {
    "overall": "NOT_STARTED",
    "sections": {
      "pre_deployment": "NOT_STARTED",
      "hardware_requirements": "NOT_STARTED",
      "access_requirements": "NOT_STARTED",
      "client_responsibilities": "NOT_STARTED",
      "provider_responsibilities": "NOT_STARTED",
      "initial_backup": "NOT_STARTED",
      "installation": "NOT_STARTED",
      "configuration": "NOT_STARTED",
      "models": "NOT_STARTED",
      "security": "NOT_STARTED",
      "acceptance_tests": "NOT_STARTED",
      "operator_training": "NOT_STARTED",
      "final_delivery": "NOT_STARTED",
      "post_deployment": "NOT_STARTED"
    }
  },
  "valid_statuses": [
    "NOT_STARTED",
    "IN_PROGRESS",
    "BLOCKED",
    "READY_FOR_ACCEPTANCE",
    "ACCEPTED"
  ],
  "psp_pix_disclaimer": "This system does NOT process real payments via PSP or PIX. Billing module operates in simulated/local mode only.",
  "legal_disclaimer": "This checklist is an operational tool only. It does not replace legal advice or the signed SOW/contract."
}
EOF

echo "Implementation checklist generated successfully:"
echo "  Markdown: ${MD_FILE}"
echo "  JSON:     ${JSON_FILE}"
echo ""
echo "AVISO: Preencha os status manualmente. Não inclua senhas ou dados sensíveis neste documento."

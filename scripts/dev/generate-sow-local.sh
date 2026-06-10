#!/usr/bin/env bash
# scripts/dev/generate-sow-local.sh
# Generates a personalized Statement of Work (SOW) from the contract template.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"
TEMPLATE="${ROOT_DIR}/contracts/SOW_TEMPLATE.md"

COMPANY_NAME=""
PROJECT_NAME=""
PLAN="Pro"
OUTPUT_DIR="${ROOT_DIR}/artifacts/contracts"

show_help() {
    cat <<EOF
Usage: $0 [options]

Options:
  --company-name NAME   (Required) Client company name
  --project-name NAME   (Required) Project name
  --plan PLAN           Plan (Basic|Pro|Enterprise Local). Default: Pro
  --output-dir DIR      Output directory. Default: artifacts/contracts
  --help                Show this help

Generates a pre-filled SOW in artifacts/contracts/<timestamp>/<safe-name>-sow.md
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --company-name) COMPANY_NAME="$2"; shift 2 ;;
        --project-name) PROJECT_NAME="$2"; shift 2 ;;
        --plan) PLAN="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --help) show_help ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
done

if [[ -z "${COMPANY_NAME}" ]] || [[ -z "${PROJECT_NAME}" ]]; then
    echo "Error: --company-name and --project-name are required"
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

OUTPUT_FILE="${OUTPUT_DIR_FULL}/${SAFE_COMPANY}-sow.md"

DATE_STR=$(date "+%Y-%m-%d")

sed \
    -e "s/\[Nome da Empresa Contratante\]/${COMPANY_NAME}/g" \
    -e "s/\[Nome da Empresa Prestadora\]/Local AI Solutions/g" \
    -e "s/\[00\.000\.000\/0001-00\]/XX.XXX.XXX\/XXXX-XX/g" \
    -e "s/\[Endereço completo\]/\[Endereço a preencher\]/g" \
    -e "s/{{DATE}}/${DATE_STR}/g" \
    -e "s/\[projeto\]/${PROJECT_NAME}/g" \
    "${TEMPLATE}" > "${OUTPUT_FILE}"

echo "SOW generated successfully:"
echo "  ${OUTPUT_FILE}"
echo ""
echo "AVISO: Este documento é um template e requer revisão jurídica antes de qualquer assinatura."
echo "AVISO: Revise todos os placeholders antes do uso."

#!/usr/bin/env bash
set -Eeuo pipefail

# validate-anthropic-real-provider.sh
# Validates Anthropic real provider with cost control, sanitized logs, and billing BRL.
# Usage:
#   ./scripts/validators/validate-anthropic-real-provider.sh --dry-run
#   ./scripts/validators/validate-anthropic-real-provider.sh --real [--model claude-3-haiku-20240307] [--max-cost-brl 2.00]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PYTHON="${PYTHON:-${PROJECT_ROOT}/.venv/bin/python}"
[[ -x "${PYTHON}" ]] || PYTHON="python3"

VALIDATOR="${SCRIPT_DIR}/lib/anthropic_real_validator.py"
ENV_LOCAL="${PROJECT_ROOT}/.env.local"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

source "${SCRIPT_DIR}/../dev/lib/real-provider-env.sh"

echo ""
echo "=================================================="
echo "  Anthropic Real Provider Validation"
echo "=================================================="
echo ""

MODE=""
ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      ARGS+=("--dry-run")
      MODE="dry-run"
      shift
      ;;
    --real)
      ARGS+=("--real")
      MODE="real"
      shift
      ;;
    --model)
      ARGS+=("--model" "${2:-}")
      shift 2
      ;;
    --max-cost-brl)
      ARGS+=("--max-cost-brl" "${2:-}")
      shift 2
      ;;
    --output-dir)
      ARGS+=("--output-dir" "${2:-}")
      shift 2
      ;;
    --help)
      echo "Usage: $0 [--dry-run | --real] [--model MODEL] [--max-cost-brl BRL] [--output-dir DIR]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [[ -z "$MODE" ]]; then
  echo -e "${YELLOW}[WARN]${NC} No mode specified. Use --dry-run or --real."
  echo "Usage: $0 [--dry-run | --real] [options]"
  exit 1
fi

if [[ ! -f "$ENV_LOCAL" ]]; then
  echo -e "${RED}[FAIL]${NC} .env.local not found"
  echo "  Create it: cp .env.example .env.local"
  exit 1
fi

set -a
source "$ENV_LOCAL"
set +a

if [[ "$MODE" == "real" ]]; then
  RPV="${REAL_PROVIDER_VALIDATION_ENABLED:-false}"
  APE="${ANTHROPIC_PROVIDER_ENABLED:-false}"
  KEY="${ANTHROPIC_API_KEY:-}"

  if [[ "$RPV" != "true" && "$RPV" != "1" ]]; then
    echo -e "${YELLOW}[SKIP]${NC} REAL_PROVIDER_VALIDATION_ENABLED is not true"
    echo "  ANTHROPIC_REAL_SKIP"
    exit 0
  fi
  if [[ "$APE" != "true" && "$APE" != "1" ]]; then
    echo -e "${YELLOW}[SKIP]${NC} ANTHROPIC_PROVIDER_ENABLED is not true"
    echo "  ANTHROPIC_REAL_SKIP"
    exit 0
  fi
  if [[ -z "$KEY" ]]; then
    echo -e "${YELLOW}[SKIP]${NC} ANTHROPIC_API_KEY is empty"
    echo "  ANTHROPIC_REAL_SKIP"
    exit 0
  fi
  MASKED_KEY="$(mask_provider_key "$KEY")"
  echo -e "  ${GREEN}[OK]${NC} ANTHROPIC_API_KEY=${MASKED_KEY}"
  echo -e "  ${GREEN}[OK]${NC} REAL_PROVIDER_VALIDATION_ENABLED=${RPV}"
  echo -e "  ${GREEN}[OK]${NC} ANTHROPIC_PROVIDER_ENABLED=${APE}"
  echo ""
fi

echo "  Mode: ${MODE}"
echo ""

"$PYTHON" "$VALIDATOR" "${ARGS[@]}"
EXIT_CODE=$?

OUTPUT_DIR="${PROJECT_ROOT}/artifacts/real-provider-validation/anthropic"
if [[ -d "$OUTPUT_DIR" ]]; then
  echo ""
  echo "  Scanning artifacts for key leaks..."
  if assert_no_provider_key_leak "$OUTPUT_DIR"; then
    echo -e "  ${GREEN}[PASS]${NC} No key leaks in artifacts"
  else
    echo -e "  ${RED}[FAIL]${NC} Key leak detected in artifacts/"
    EXIT_CODE=1
  fi
fi

echo ""
echo "=================================================="
echo "  Done."
echo "=================================================="

exit "$EXIT_CODE"

echo 'Running artifacts scanner...'
./scripts/dev/scan-real-provider-artifacts.sh --path "${OUT_PATH:-$OUTPUT_DIR}" --redact --fail-on-findings

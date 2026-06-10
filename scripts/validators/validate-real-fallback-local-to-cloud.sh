#!/usr/bin/env bash
set -Eeuo pipefail

# validate-real-fallback-local-to-cloud.sh
# Validates fallback local -> cloud with simulated local failure,
# cost control, sanitized logs, and billing tracking.
# Usage:
#   ./scripts/validators/validate-real-fallback-local-to-cloud.sh --dry-run
#   ./scripts/validators/validate-real-fallback-local-to-cloud.sh --real --provider auto

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PYTHON="${PYTHON:-${PROJECT_ROOT}/.venv/bin/python}"
[[ -x "${PYTHON}" ]] || PYTHON="python3"

VALIDATOR="${SCRIPT_DIR}/lib/fallback_validator.py"
ENV_LOCAL="${PROJECT_ROOT}/.env.local"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

source "${SCRIPT_DIR}/../dev/lib/real-provider-env.sh"

echo ""
echo "=================================================="
echo "  Fallback Local-to-Cloud Validation"
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
    --provider)
      ARGS+=("--provider" "${2:-}")
      shift 2
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
      echo "Usage: $0 [--dry-run | --real] [--provider openai|deepseek|anthropic|auto] [--model MODEL] [--max-cost-brl BRL] [--output-dir DIR]"
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

  if [[ "$RPV" != "true" && "$RPV" != "1" ]]; then
    echo -e "${YELLOW}[SKIP]${NC} REAL_PROVIDER_VALIDATION_ENABLED is not true"
    echo "  FALLBACK_REAL_SKIP"
    exit 0
  fi

  # Check at least one cloud provider is configured
  CLOUD_OK=false
  for prov_var in OPENAI_API_KEY ANTHROPIC_API_KEY DEEPSEEK_API_KEY; do
    key_val="${!prov_var:-}"
    if [[ -n "$key_val" ]]; then
      CLOUD_OK=true
      break
    fi
  done

  if [[ "$CLOUD_OK" == "false" ]]; then
    echo -e "${YELLOW}[SKIP]${NC} No cloud provider configured (API keys all empty)"
    echo "  FALLBACK_REAL_SKIP"
    exit 0
  fi

  # Mask keys for display
  for prov_var in OPENAI_API_KEY ANTHROPIC_API_KEY DEEPSEEK_API_KEY; do
    key_val="${!prov_var:-}"
    if [[ -n "$key_val" ]]; then
      MASKED="$(mask_provider_key "$key_val")"
      echo -e "  ${GREEN}[OK]${NC} ${prov_var}=${MASKED}"
    fi
  done

  echo -e "  ${GREEN}[OK]${NC} REAL_PROVIDER_VALIDATION_ENABLED=${RPV}"
  echo ""
fi

echo "  Mode: ${MODE}"
echo ""

# Save original and set force failure flag before validator
ORIG_FORCE="${ROUTING_TEST_FORCE_LOCAL_FAILURE:-false}"

# Run the Python validator
"$PYTHON" "$VALIDATOR" "${ARGS[@]}"
EXIT_CODE=$?

# Clean up force failure flag
export ROUTING_TEST_FORCE_LOCAL_FAILURE="$ORIG_FORCE"

OUTPUT_DIR="${PROJECT_ROOT}/artifacts/real-provider-validation/fallback"
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
echo "  Original force-local-failure restored: ${ORIG_FORCE}"
echo "=================================================="

exit "$EXIT_CODE"

echo 'Running artifacts scanner...'
./scripts/dev/scan-real-provider-artifacts.sh --path "${OUT_PATH:-$OUTPUT_DIR}" --redact --fail-on-findings

#!/bin/bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}[PASS]${NC} $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; exit 1; }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; }

echo "Validating local LLM harness integration environment..."

: "${LLM_HARNESS_LOCAL_BASE_URL:=}"
: "${LLM_HARNESS_LOCAL_MODEL:=}"
: "${LLM_HARNESS_RUN_LOCAL_LLM_TESTS:=}"
: "${LLM_HARNESS_LOCAL_API_KEY:=}"

[[ "${LLM_HARNESS_RUN_LOCAL_LLM_TESTS}" == "1" ]] \
  && pass "LLM_HARNESS_RUN_LOCAL_LLM_TESTS=1" \
  || fail "Set LLM_HARNESS_RUN_LOCAL_LLM_TESTS=1 to enable real local integration tests"

[[ -n "${LLM_HARNESS_LOCAL_BASE_URL}" ]] \
  && pass "LLM_HARNESS_LOCAL_BASE_URL=${LLM_HARNESS_LOCAL_BASE_URL}" \
  || fail "LLM_HARNESS_LOCAL_BASE_URL is required (example: http://localhost:8000/v1)"

[[ -n "${LLM_HARNESS_LOCAL_MODEL}" ]] \
  && pass "LLM_HARNESS_LOCAL_MODEL=${LLM_HARNESS_LOCAL_MODEL}" \
  || fail "LLM_HARNESS_LOCAL_MODEL is required"

MODELS_URL="${LLM_HARNESS_LOCAL_BASE_URL%/}"
if [[ "${MODELS_URL}" == */v1/models ]]; then
  :
elif [[ "${MODELS_URL}" == */v1 ]]; then
  MODELS_URL="${MODELS_URL}/models"
else
  MODELS_URL="${MODELS_URL}/v1/models"
fi

AUTH_ARGS=()
if [[ -n "${LLM_HARNESS_LOCAL_API_KEY}" ]]; then
  AUTH_ARGS=(-H "Authorization: Bearer ${LLM_HARNESS_LOCAL_API_KEY}")
else
  warn "LLM_HARNESS_LOCAL_API_KEY not set; continuing without Authorization header"
fi

if curl -fsS --connect-timeout 5 --max-time 20 "${AUTH_ARGS[@]}" "${MODELS_URL}" > /tmp/llm_harness_local_models.json; then
  pass "Local endpoint responded at ${MODELS_URL}"
else
  fail "Could not reach ${MODELS_URL}. Start Ollama/vLLM/LM Studio and confirm the base URL."
fi

if .venv/bin/python - <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/tmp/llm_harness_local_models.json").read_text())
models = data["data"] if isinstance(data, dict) and "data" in data else data
assert isinstance(models, list) and len(models) > 0
print(models[0].get("id", "unknown"))
PY
then
  pass "Model list endpoint returned at least one model"
else
  fail "The models payload did not contain a non-empty list"
fi

echo "Environment is ready. Run:"
echo "  make integration-local-llm-harness"

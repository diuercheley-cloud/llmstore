#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

source "${ROOT_DIR}/scripts/dev/common.sh"

MODEL_ID="${1:-unsloth/gemma-4-E4B-it-GGUF}"
BASE_URL=$(default_base_url)

echo "### Inciando Benchmark para: ${MODEL_ID} ###"

curl_base_url "${BASE_URL}/admin/performance/benchmark?model_id=${MODEL_ID}" \
  -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" | python3 -m json.tool

echo "### Benchmark Concluído ###"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

MODEL_ID="${1:?usage: ./scripts/deploy/register-model.sh MODEL_ID MODEL_FILE [MODEL_ALIAS] [PROVIDER] [CONTEXT_LENGTH] [IS_DEFAULT] [BACKEND_ID]}"
MODEL_FILE="${2:?usage: ./scripts/deploy/register-model.sh MODEL_ID MODEL_FILE [MODEL_ALIAS] [PROVIDER] [CONTEXT_LENGTH] [IS_DEFAULT] [BACKEND_ID]}"
MODEL_ALIAS="${3:-}"
PROVIDER="${4:-llama.cpp}"
CONTEXT_LENGTH="${5:-2048}"
IS_DEFAULT="${6:-false}"
BACKEND_ID="${7:-}"

PAYLOAD="$(
python3 -c '
import json, sys
payload = {
    "model_id": sys.argv[1],
    "model_alias": sys.argv[3] or None,
    "inference_backend_id": sys.argv[7] or None,
    "provider": sys.argv[4],
    "model_file": sys.argv[2],
    "context_length": int(sys.argv[5]),
    "is_active": True,
    "is_default": sys.argv[6].lower() == "true",
    "status": "configured",
}
print(json.dumps(payload))
' "${MODEL_ID}" "${MODEL_FILE}" "${MODEL_ALIAS}" "${PROVIDER}" "${CONTEXT_LENGTH}" "${IS_DEFAULT}" "${BACKEND_ID}"
)"

curl -fsS "${BASE_URL}/admin/models" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}" | python3 -m json.tool

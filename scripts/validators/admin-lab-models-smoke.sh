#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
if [[ -z "${ADMIN_TOKEN}" ]]; then
  printf 'ADMIN_TOKEN is required.\n' >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

auth() {
  local url="$1"
  shift
  curl -fsS -H "X-Admin-Token: ${ADMIN_TOKEN}" "$@" "${url}"
}

echo "--- Admin Lab Models Smoke Test ---"

echo "Checking model endpoints..."
auth "${BASE_URL}/admin/models" > "${TMP_DIR}/models.json"
auth "${BASE_URL}/admin/models/files" > "${TMP_DIR}/files.json"
echo "OK: /admin/models and /admin/models/files responding."

GEMMA_ID="$(
python3 - "${TMP_DIR}/models.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
for item in data.get("registry", []):
    if item.get("model_alias") == "gemma" or item.get("is_default"):
        print(item["id"])
        raise SystemExit
raise SystemExit("gemma/default model not found")
PY
)"

echo "Testing prompt on Gemma..."
auth "${BASE_URL}/admin/models/${GEMMA_ID}/test-prompt" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Responda com uma frase curta confirmando o funcionamento do modelo.","max_tokens":64,"temperature":0.2,"stream":false,"include_reasoning":false}' \
  > "${TMP_DIR}/gemma-test.json"
echo "OK: Gemma prompt test completed."

BACKEND_ID="$(
python3 - "${TMP_DIR}/models.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
backends = data.get("backends", [])
for item in backends:
    if item.get("name") == "gemma-local":
        print(item["id"])
        raise SystemExit
if backends:
    print(backends[0]["id"])
PY
)"

TEST_FILE="$(
python3 - "${TMP_DIR}/files.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], 'r', encoding='utf-8'))
for item in data.get("files", []):
    if not item.get("already_registered"):
        print(item["filename"])
        raise SystemExit
for item in data.get("files", []):
    print(item["filename"])
    raise SystemExit
PY
)"

if [[ -n "${TEST_FILE}" ]]; then
  TEST_ALIAS="ui-smoke-$(date +%s)"
  TEST_MODEL_ID="smoke/${TEST_ALIAS}"
  echo "Creating temporary model using ${TEST_FILE}..."
  auth "${BASE_URL}/admin/models" \
    -H "Content-Type: application/json" \
    -d "{\"display_name\":\"Smoke Model\",\"model_id\":\"${TEST_MODEL_ID}\",\"model_alias\":\"${TEST_ALIAS}\",\"provider\":\"llama.cpp\",\"model_file\":\"${TEST_FILE}\",\"inference_backend_id\":\"${BACKEND_ID}\",\"context_length\":4096,\"is_active\":true,\"is_default\":false,\"status\":\"configured\",\"prompt_template\":\"auto\"}" \
    > "${TMP_DIR}/created-model.json"
  TEST_MODEL_UUID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' < "${TMP_DIR}/created-model.json")"
  echo "OK: Temporary model created (${TEST_MODEL_UUID})."

  echo "Checking duplicate alias protection..."
  if curl -sS -o /dev/null -w '%{http_code}' -H "X-Admin-Token: ${ADMIN_TOKEN}" -H "Content-Type: application/json" \
      -d "{\"display_name\":\"Smoke Duplicate\",\"model_id\":\"${TEST_MODEL_ID}-dup\",\"model_alias\":\"${TEST_ALIAS}\",\"provider\":\"llama.cpp\",\"model_file\":\"${TEST_FILE}\",\"inference_backend_id\":\"${BACKEND_ID}\",\"context_length\":4096,\"is_active\":true,\"is_default\":false,\"status\":\"configured\",\"prompt_template\":\"auto\"}" \
      "${BASE_URL}/admin/models" \
      | grep -q '^409$'; then
    echo "OK: Duplicate alias blocked."
  else
    echo "FAIL: Duplicate alias was not blocked." >&2
    exit 1
  fi

  echo "Disabling and enabling temporary model..."
  auth "${BASE_URL}/admin/models/${TEST_MODEL_UUID}/disable" -X POST > /dev/null
  auth "${BASE_URL}/admin/models/${TEST_MODEL_UUID}/enable" -X POST > /dev/null
  echo "OK: Toggle model completed."

  echo "Soft deleting temporary model..."
  auth "${BASE_URL}/admin/models/${TEST_MODEL_UUID}" \
    -X DELETE -H "Content-Type: application/json" \
    -d '{"confirm_route_removal":true,"mode":"soft"}' \
    > /dev/null
  echo "OK: Temporary model removed safely."
else
  echo "SKIP: No GGUF file available for temporary model registration."
fi

echo "Resetting backend circuit breaker..."
auth "${BASE_URL}/admin/backends/circuit-breaker/reset" -X POST > /dev/null
echo "OK: Circuit breaker reset."

echo "--- Admin Lab Models Smoke Test PASSED ---"

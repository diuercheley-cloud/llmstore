#!/usr/bin/env bash
set -euo pipefail

# OpenCode Validation Script for Qwen Model
# This script simulates an OpenCode connection to the API.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
MODEL_ALIAS="qwen"
API_KEY="sk-local-nC3TfUWgAeAhWA0jrLlDvF8LiDfY0aly"

printf "=== OpenCode API Validation (Qwen) ===\n"

# 1. Validate Base URL
printf "[INFO] Using Base URL: %s\n" "${BASE_URL}"
if curl -fsS "${BASE_URL}/health" >/dev/null; then
    printf "[OK] Control Plane is Online.\n"
else
    printf "[FAIL] Control Plane is Offline.\n"
    exit 1
fi

# 2. Check if model is available via API
printf "[INFO] Verifying if model '%s' is available in /v1/models...\n" "${MODEL_ALIAS}"
MODEL_CHECK=$(curl -s -H "Authorization: Bearer ${API_KEY}" "${BASE_URL}/v1/models" | grep "${MODEL_ALIAS}")

if [[ -n "${MODEL_CHECK}" ]]; then
    printf "[OK] Model '%s' found in API list.\n" "${MODEL_ALIAS}"
else
    printf "[FAIL] Model '%s' NOT found in API list for this API Key.\n" "${MODEL_ALIAS}"
    exit 1
fi

# 3. Simulate OpenCode Chat Request
printf "[INFO] Sending Chat Completion request (simulating OpenCode)...\n"
printf "[INFO] Model: %s\n" "${MODEL_ALIAS}"

# We use a longer timeout because 35B models take time to load first time
RESPONSE=$(curl -s -w "\n%{http_code}" --max-time 300 "${BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL_ALIAS}\",
    \"messages\": [
        {\"role\": \"system\", \"content\": \"Você é um assistente prestativo.\"},
        {\"role\": \"user\", \"content\": \"Olá! Quem é você?\"}
    ],
    \"temperature\": 0.7,
    \"max_tokens\": 50,
    \"stream\": false
  }")

HTTP_STATUS=$(echo "${RESPONSE}" | tail -n1)
BODY=$(echo "${RESPONSE}" | sed '$d')

if [[ "${HTTP_STATUS}" == "200" ]]; then
    printf "[SUCCESS] OpenCode connection validated!\n"
    CONTENT=$(echo "${BODY}" | python3 -c 'import json, sys; print(json.load(sys.stdin)["choices"][0]["message"]["content"])')
    printf "Response from Qwen: %s\n" "${CONTENT}"
else
    printf "[FAIL] API call failed with HTTP %s\n" "${HTTP_STATUS}"
    printf "Error Detail: %s\n" "${BODY}"
    
    printf "\n=== Diagnostics ===\n"
    printf "1. Check if 'data-plane-bonsai' is running: 'docker compose ps'\n"
    printf "2. Check logs: 'docker compose logs -f data-plane-bonsai'\n"
    printf "3. Common 404: Model alias mismatch or billing plan restriction.\n"
    printf "4. Common 503: Model still loading into GPU memory.\n"
    exit 1
fi

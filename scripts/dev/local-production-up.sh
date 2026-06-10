#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

printf '[up] Initing local production stack...\n'
cd "${ROOT_DIR}"

# Ensure environment file exists
if [[ ! -f "${ROOT_DIR}/${STACK_ENV_FILE}" ]]; then
  cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/${STACK_ENV_FILE}"
  printf '[up] Created %s from .env.example\n' "${STACK_ENV_FILE}"
fi

# Build and start
dc up -d --build

printf '[up] Waiting for services to be ready...\n'
MAX_RETRIES=30
RETRY_COUNT=0
BASE_URL="$(default_base_url)"

until curl -fsS "${BASE_URL}/ready" >/dev/null 2>&1; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [[ ${RETRY_COUNT} -ge ${MAX_RETRIES} ]]; then
    printf '[up] ERROR: Timeout waiting for /ready\n'
    exit 1
  fi
  printf '.'
  sleep 2
done
printf ' OK\n'

# Create demo client if not exists
printf '[up] Ensuring demo client exists...\n'
DEMO_CLIENT_ID="$(lookup_demo_client_id "${BASE_URL}")" || true
if [[ -z "${DEMO_CLIENT_ID}" ]]; then
  printf '[up] Creating demo client...\n'
  DEMO_OUTPUT="$("${SCRIPT_DIR}/create-customer-demo.sh" "demo-client" "Demo Client for Local Production" "free")"
  DEMO_API_KEY="$(printf '%s\n' "${DEMO_OUTPUT}" | awk -F= '/^api_key=/{print $2}')"
  printf '[up] Demo API Key: %s (Save it! Only shown once)\n' "${DEMO_API_KEY}"
  DEMO_KEY_SUMMARY="[SHOWN_ONCE_NOT_SAVED]"
else
  printf '[up] Demo client already exists.\n'
  DEMO_KEY_SUMMARY="[ALREADY_EXISTS]"
fi

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
ARTIFACT_DIR="${ROOT_DIR}/artifacts/local-production/${TIMESTAMP}"
mkdir -p "${ARTIFACT_DIR}"

SUMMARY_FILE="${ARTIFACT_DIR}/summary.txt"
{
  echo "Local Production Stack Summary"
  echo "=============================="
  echo "Timestamp: ${TIMESTAMP}"
  echo "Base URL: ${BASE_URL}"
  echo "Landing: ${BASE_URL}/"
  echo "Pricing: ${BASE_URL}/pricing"
  echo "Signup: ${BASE_URL}/signup"
  echo "Client Portal: ${BASE_URL}/client-portal"
  echo "Admin Dashboard: ${BASE_URL}/admin-dashboard"
  echo "Admin Lab: ${BASE_URL}/admin-lab"
  echo "------------------------------"
  echo "Demo API Key: ${DEMO_KEY_SUMMARY}"
  echo "Admin Token: [SEE_ENV]"
} > "${SUMMARY_FILE}"

printf '\n--- LOCAL PRODUCTION READY ---\n'
cat "${SUMMARY_FILE}"
printf -- '------------------------------\n'
printf 'Summary saved to: %s\n' "${SUMMARY_FILE}"

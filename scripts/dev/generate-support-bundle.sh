#!/usr/bin/env bash
set -euo pipefail

# scripts/dev/generate-support-bundle.sh
# Triggers and downloads a support bundle for diagnostic purposes.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"

init_stack_env

BASE_URL="${1:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

if [[ -z "${ADMIN_TOKEN}" ]]; then
  echo "Error: ADMIN_TOKEN is not set."
  exit 1
fi

echo "--- Generating Support Bundle ---"
RESPONSE=$(curl_base_url "${BASE_URL}/admin/support/bundle" -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" -s)

FILENAME=$(echo "${RESPONSE}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('filename', ''))")

if [[ -z "${FILENAME}" ]]; then
  echo "Error generating bundle: ${RESPONSE}"
  exit 1
fi

echo "Bundle generated: ${FILENAME}"

echo "--- Downloading Latest Bundle ---"
curl_base_url "${BASE_URL}/admin/support/bundle/latest" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -o "artifacts/support-bundles/${FILENAME}" -s

echo "Bundle saved to: artifacts/support-bundles/${FILENAME}"
echo "You can now share this file with support for diagnosis."
echo "Note: Sensitive data (keys, tokens, prompts) has been redacted."

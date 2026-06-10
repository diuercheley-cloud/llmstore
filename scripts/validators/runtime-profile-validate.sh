#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../" && pwd)"

source "${ROOT_DIR}/scripts/dev/common.sh"
init_stack_env

PROFILE_ID="${1:-}"
if [[ -z "${PROFILE_ID}" ]]; then
  echo "Error: profile_id is required."
  echo "Usage: $0 <profile_id>"
  exit 1
fi

BASE_URL=$(default_base_url)

echo "### Validating Runtime Profile: ${PROFILE_ID} ###"
curl_base_url "${BASE_URL}/admin/runtime-profiles/validate" \
  -s \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -d "{\"profile_id\": \"${PROFILE_ID}\"}" | python3 -m json.tool

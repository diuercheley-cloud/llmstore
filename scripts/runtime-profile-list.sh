#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${ROOT_DIR}/scripts/common.sh"
init_stack_env

BASE_URL=$(default_base_url)

echo "### Available Runtime Profiles ###"
curl_base_url "${BASE_URL}/admin/runtime-profiles" \
  -s \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool

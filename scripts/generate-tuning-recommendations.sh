#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${ROOT_DIR}/scripts/common.sh"

BASE_URL=$(default_base_url)

echo "### Buscando Recomendações de Tuning ###"

curl_base_url "${BASE_URL}/admin/performance/recommendations" \
  -X GET \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${ROOT_DIR}/scripts/common.sh"

PROFILE_NAME="${1:-balanced}"
BASE_URL=$(default_base_url)

echo "### Aplicando Perfil de Tuning: ${PROFILE_NAME} ###"

curl_base_url "${BASE_URL}/admin/performance/apply-profile?profile_name=${PROFILE_NAME}" \
  -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool

echo "Nota: Se RUNTIME_TUNING_APPLY_ENABLED não estiver definido como true no ambiente, esta ação será apenas ADVISORY."

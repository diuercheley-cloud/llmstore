#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN}"
FORMAT="${FORMAT:-json}"
CLIENT_ID="${CLIENT_ID:-}"
START_DATE="${START_DATE:-}"
END_DATE="${END_DATE:-}"

query=("format=${FORMAT}")
if [[ -n "${CLIENT_ID}" ]]; then
  query+=("client_id=${CLIENT_ID}")
fi
if [[ -n "${START_DATE}" ]]; then
  query+=("start_date=${START_DATE}")
fi
if [[ -n "${END_DATE}" ]]; then
  query+=("end_date=${END_DATE}")
fi

curl -fsS "${BASE_URL}/admin/export/usage?$(IFS='&'; echo "${query[*]}")" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}"

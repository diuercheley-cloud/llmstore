#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

curl_base_url "${BASE_URL}/admin/backends/circuit-breaker/reset" -fsS \
  -X POST \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool

printf '\n[reset-circuit-breaker] note: the circuit breaker lives in memory inside the control-plane process.\n'
printf '[reset-circuit-breaker] a control-plane restart also clears it.\n'

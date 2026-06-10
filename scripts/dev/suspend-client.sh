#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env
BASE_URL="${BASE_URL:-$(default_base_url)}"
CLIENT_ID="${1:-${CLIENT_ID:-}}"
CLIENT_ID="${CLIENT_ID:?usage: ./scripts/dev/suspend-client.sh <client-id>}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN}"

curl -fsS -X POST "${BASE_URL}/admin/security/clients/${CLIENT_ID}/suspend" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" | python3 -m json.tool

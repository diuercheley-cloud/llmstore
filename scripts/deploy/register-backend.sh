#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/../dev/common.sh"
init_stack_env

BASE_URL="${BASE_URL:-$(default_base_url)}"
ADMIN_TOKEN="${ADMIN_TOKEN:?set ADMIN_TOKEN in environment or env file}"

NAME="${1:?usage: ./scripts/deploy/register-backend.sh NAME PROVIDER BACKEND_URL [HEALTHCHECK_PATH] [IS_DEFAULT]}"
PROVIDER="${2:?usage: ./scripts/deploy/register-backend.sh NAME PROVIDER BACKEND_URL [HEALTHCHECK_PATH] [IS_DEFAULT]}"
BACKEND_URL="${3:?usage: ./scripts/deploy/register-backend.sh NAME PROVIDER BACKEND_URL [HEALTHCHECK_PATH] [IS_DEFAULT]}"
HEALTHCHECK_PATH="${4:-/health}"
IS_DEFAULT="${5:-false}"

PAYLOAD="$(
python3 -c '
import json, sys
print(json.dumps({
    "name": sys.argv[1],
    "provider": sys.argv[2],
    "backend_url": sys.argv[3],
    "healthcheck_path": sys.argv[4],
    "is_active": True,
    "is_default": sys.argv[5].lower() == "true",
    "status": "configured",
}))
' "${NAME}" "${PROVIDER}" "${BACKEND_URL}" "${HEALTHCHECK_PATH}" "${IS_DEFAULT}"
)"

curl -fsS "${BASE_URL}/admin/backends" \
  -H "X-Admin-Token: ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}" | python3 -m json.tool

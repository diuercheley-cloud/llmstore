#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/common.sh"
init_stack_env
BASE_URL="${BASE_URL:-$(default_base_url)}"
JOB_ID="${1:-${JOB_ID:-}}"
JOB_ID="${JOB_ID:?usage: ./scripts/cancel-job.sh <job-id>}"
API_KEY="$(require_api_key "${BASE_URL}" "cancel-job")"
API_KEY="${API_KEY:?set API_KEY or configure ADMIN_TOKEN to mint a demo key}"

curl -fsS -X DELETE "${BASE_URL}/v1/jobs/${JOB_ID}/cancel" \
  -H "Authorization: Bearer ${API_KEY}" | python3 -m json.tool
